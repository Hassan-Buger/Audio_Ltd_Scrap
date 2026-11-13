"""Durable URL Frontier repository."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session
from app.database.models.url import CrawlURL
from app.database.models.job import CrawlJob
from app.schemas.crawl import URLStatus, URLType
from app.crawler.url_normalizer import normalize_url, classify_url, is_allowed_host


class URLRepository:
    @staticmethod
    def enqueue_url(
        db: Session,
        job_id: int,
        raw_url: str,
        depth: int = 0,
        forced_type: Optional[URLType] = None
    ) -> Optional[CrawlURL]:
        """Insert a URL into the frontier idempotently if host is allowed."""
        if not is_allowed_host(raw_url):
            return None

        norm_url = normalize_url(raw_url)
        url_type = forced_type or classify_url(norm_url)

        # Check if already present for this job
        existing = db.execute(
            select(CrawlURL).where(
                and_(CrawlURL.crawl_job_id == job_id, CrawlURL.normalized_url == norm_url)
            )
        ).scalar_one_or_none()

        if existing:
            return existing

        crawl_url = CrawlURL(
            crawl_job_id=job_id,
            url=raw_url,
            normalized_url=norm_url,
            url_type=url_type.value if hasattr(url_type, "value") else str(url_type),
            status=URLStatus.QUEUED.value,
            depth=depth,
            attempts=0,
            max_attempts=3,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(crawl_url)
        db.flush()

        # Update job counter
        db.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job_id)
            .values(urls_discovered=CrawlJob.urls_discovered + 1)
        )
        return crawl_url

    @staticmethod
    def enqueue_batch(
        db: Session,
        job_id: int,
        raw_urls: List[str],
        depth: int = 0
    ) -> int:
        """Enqueue multiple URLs idempotently; returns count of newly enqueued URLs."""
        count = 0
        for raw_url in raw_urls:
            res = URLRepository.enqueue_url(db, job_id, raw_url, depth=depth)
            if res and res.attempts == 0 and res.status == URLStatus.QUEUED.value:
                count += 1
        return count

    @staticmethod
    def claim_urls(
        db: Session,
        job_id: int,
        worker_id: str,
        batch_size: int = 20,
        lease_seconds: int = 300
    ) -> List[CrawlURL]:
        """Claim a batch of queued URLs using a lease timestamp to prevent worker collisions."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=lease_seconds)

        # First reclaim expired leases for this job
        URLRepository.reclaim_expired_leases(db, job_id)

        # Find eligible queued URLs
        stmt = (
            select(CrawlURL)
            .where(
                and_(
                    CrawlURL.crawl_job_id == job_id,
                    CrawlURL.status == URLStatus.QUEUED.value,
                    CrawlURL.attempts < CrawlURL.max_attempts
                )
            )
            .order_by(CrawlURL.depth.asc(), CrawlURL.id.asc())
            .limit(batch_size)
        )
        items = list(db.execute(stmt).scalars().all())

        if not items:
            return []

        item_ids = [item.id for item in items]
        db.execute(
            update(CrawlURL)
            .where(CrawlURL.id.in_(item_ids))
            .values(
                status=URLStatus.IN_PROGRESS.value,
                lease_id=worker_id,
                lease_expires_at=expires_at,
                attempts=CrawlURL.attempts + 1,
                updated_at=now
            )
        )
        db.flush()
        return items

    @staticmethod
    def mark_processed(db: Session, url_id: int, http_status: int = 200) -> None:
        """Mark a claimed URL as successfully processed."""
        now = datetime.now(timezone.utc)
        crawl_url = db.get(CrawlURL, url_id)
        if crawl_url:
            crawl_url.status = URLStatus.PROCESSED.value
            crawl_url.http_status = http_status
            crawl_url.lease_id = None
            crawl_url.lease_expires_at = None
            crawl_url.updated_at = now

            # Increment job counter
            db.execute(
                update(CrawlJob)
                .where(CrawlJob.id == crawl_url.crawl_job_id)
                .values(urls_processed=CrawlJob.urls_processed + 1)
            )
            db.flush()

    @staticmethod
    def mark_failed(
        db: Session,
        url_id: int,
        error_msg: str,
        is_retryable: bool = True,
        http_status: Optional[int] = None,
        is_inaccessible: bool = False
    ) -> None:
        """Record an error for a URL, deciding retryability and access-restriction status."""
        now = datetime.now(timezone.utc)
        crawl_url = db.get(CrawlURL, url_id)
        if not crawl_url:
            return

        crawl_url.http_status = http_status
        crawl_url.last_error = error_msg
        crawl_url.lease_id = None
        crawl_url.lease_expires_at = None
        crawl_url.updated_at = now

        if is_inaccessible or http_status in (401, 403, 405):
            crawl_url.status = URLStatus.INACCESSIBLE.value
        elif is_retryable and crawl_url.attempts < crawl_url.max_attempts:
            crawl_url.status = URLStatus.FAILED_RETRYABLE.value
        else:
            crawl_url.status = URLStatus.FAILED_TERMINAL.value

        db.flush()

    @staticmethod
    def reclaim_expired_leases(db: Session, job_id: Optional[int] = None) -> int:
        """Reset in_progress URLs whose leases have expired back to queued."""
        now = datetime.now(timezone.utc)
        conditions = [
            CrawlURL.status == URLStatus.IN_PROGRESS.value,
            CrawlURL.lease_expires_at < now
        ]
        if job_id is not None:
            conditions.append(CrawlURL.crawl_job_id == job_id)

        stmt = (
            update(CrawlURL)
            .where(and_(*conditions))
            .values(
                status=URLStatus.QUEUED.value,
                lease_id=None,
                lease_expires_at=None,
                updated_at=now
            )
            .execution_options(synchronize_session=False)
        )
        result = db.execute(stmt)
        db.flush()
        return result.rowcount
