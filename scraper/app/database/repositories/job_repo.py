"""Crawl Job repository for job creation, progress tracking, and error logging."""
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update, func, desc, and_
from sqlalchemy.orm import Session
from app.database.models.job import CrawlJob, ScrapeRun, ScrapeError
from app.database.models.url import CrawlURL
from app.schemas.job import JobStatus, JobScope, CrawlJobProgressResponse, CrawlJobErrorItem
from app.schemas.crawl import URLStatus


class JobRepository:
    @staticmethod
    def create_job(
        db: Session,
        scope: JobScope = JobScope.FULL,
        config: Optional[Dict[str, Any]] = None
    ) -> CrawlJob:
        now = datetime.now(timezone.utc)
        job = CrawlJob(
            scope=scope.value if hasattr(scope, "value") else str(scope),
            status=JobStatus.QUEUED.value,
            config=config or {},
            urls_discovered=0,
            urls_processed=0,
            products_extracted=0,
            created_at=now
        )
        db.add(job)
        db.flush()
        return job

    @staticmethod
    def get_job(db: Session, job_id: int) -> Optional[CrawlJob]:
        return db.get(CrawlJob, job_id)

    @staticmethod
    def list_jobs(db: Session, skip: int = 0, limit: int = 50) -> List[CrawlJob]:
        stmt = select(CrawlJob).order_by(desc(CrawlJob.id)).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_status(db: Session, job_id: int, status: JobStatus) -> Optional[CrawlJob]:
        job = db.get(CrawlJob, job_id)
        if not job:
            return None

        now = datetime.now(timezone.utc)
        job.status = status.value if hasattr(status, "value") else str(status)

        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = now
        elif status in (JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS, JobStatus.CANCELLED, JobStatus.FAILED):
            job.completed_at = now

        db.flush()
        return job

    @staticmethod
    def increment_product_count(db: Session, job_id: int, count: int = 1) -> None:
        db.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job_id)
            .values(products_extracted=CrawlJob.products_extracted + count)
        )
        db.flush()

    @staticmethod
    def get_progress(db: Session, job_id: int) -> Optional[CrawlJobProgressResponse]:
        job = db.get(CrawlJob, job_id)
        if not job:
            return None

        # Aggregate counts by URL status for this job
        stmt = select(CrawlURL.status, func.count(CrawlURL.id)).where(
            CrawlURL.crawl_job_id == job_id
        ).group_by(CrawlURL.status)
        counts = dict(db.execute(stmt).all())

        discovered = job.urls_discovered
        queued = counts.get(URLStatus.QUEUED.value, 0)
        in_progress = counts.get(URLStatus.IN_PROGRESS.value, 0)
        processed = counts.get(URLStatus.PROCESSED.value, 0)
        retryable = counts.get(URLStatus.FAILED_RETRYABLE.value, 0)
        terminal = counts.get(URLStatus.FAILED_TERMINAL.value, 0)
        inaccessible = counts.get(URLStatus.INACCESSIBLE.value, 0)

        # Denominator: total active actionable URLs
        total_actionable = processed + retryable + terminal + inaccessible + queued + in_progress
        pct = (processed / total_actionable * 100.0) if total_actionable > 0 else 0.0

        return CrawlJobProgressResponse(
            job_id=job.id,
            status=JobStatus(job.status),
            urls_discovered=discovered,
            urls_queued=queued,
            urls_in_progress=in_progress,
            urls_processed=processed,
            urls_failed_retryable=retryable,
            urls_failed_terminal=terminal,
            urls_inaccessible=inaccessible,
            products_extracted=job.products_extracted,
            products_incomplete=0,
            percentage_completed=round(pct, 2)
        )

    @staticmethod
    def log_error(
        db: Session,
        job_id: Optional[int],
        url: str,
        stage: str,
        error_type: str,
        error_message: str,
        is_retryable: bool = False
    ) -> ScrapeError:
        now = datetime.now(timezone.utc)
        err = ScrapeError(
            job_id=job_id,
            url=url,
            stage=stage,
            error_type=error_type,
            error_message=error_message,
            is_retryable=is_retryable,
            created_at=now
        )
        db.add(err)
        db.flush()
        return err

    @staticmethod
    def get_job_errors(db: Session, job_id: int, skip: int = 0, limit: int = 100) -> List[CrawlJobErrorItem]:
        stmt = (
            select(ScrapeError)
            .where(ScrapeError.job_id == job_id)
            .order_by(desc(ScrapeError.id))
            .offset(skip)
            .limit(limit)
        )
        items = db.execute(stmt).scalars().all()
        return [
            CrawlJobErrorItem(
                id=item.id,
                url=item.url,
                error_type=item.error_type,
                error_message=item.error_message,
                is_retryable=item.is_retryable,
                created_at=item.created_at
            )
            for item in items
        ]
