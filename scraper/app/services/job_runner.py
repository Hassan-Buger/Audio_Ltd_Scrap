"""Crawl job execution engine for processing frontier URLs."""
import logging
from typing import Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.config import settings
from app.database.models.job import CrawlJob
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.category_repo import CategoryRepository
from app.schemas.job import JobStatus
from app.schemas.crawl import URLStatus, URLType
from app.extraction.products import extract_product_detail
from app.extraction.categories import extract_category_tree, extract_listing_products
from app.extraction.pagination import extract_pagination
from app.services.raw_store import raw_store

logger = logging.getLogger(__name__)


class JobRunner:
    @staticmethod
    def process_url(db: Session, job_id: int, url_record) -> Dict[str, Any]:
        """
        Fetch and process a single crawl URL.
        1. Checks raw_store for cached HTML snapshots on disk first.
        2. If not cached, fetches from network with politeness headers.
        3. Saves raw HTML snapshot to disk before parsing.
        4. Respects site access controls and marks 403 / Cloudflare Challenges as INACCESSIBLE.
        """
        html = None
        effective_url = url_record.url
        http_status = 200

        # Check raw snapshot store first (saved HTML replay)
        cached = raw_store.load(url_record.url)
        if cached and cached.get("text"):
            html = cached["text"]
            effective_url = cached.get("final_url", url_record.url)
            http_status = cached.get("status", 200)
            logger.info(f"Loaded {url_record.url} from raw HTML snapshot cache")
        else:
            headers = {
                "User-Agent": settings.SCRAPER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "lt,en-US;q=0.7,en;q=0.3",
            }
            if settings.SCRAPER_COOKIES:
                headers["Cookie"] = settings.SCRAPER_COOKIES

            try:
                with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                    resp = client.get(url_record.url, headers=headers)
            except Exception as e:
                URLRepository.mark_failed(
                    db, url_record.id, error_msg=str(e), is_retryable=True
                )
                JobRepository.log_error(
                    db, job_id, url_record.url, stage="fetch",
                    error_type="NETWORK_ERROR", error_message=str(e), is_retryable=True
                )
                return {"status": "failed", "error": str(e)}

            # Check for access restrictions (Cloudflare Challenge, 403 Forbidden, 401 Unauthorized)
            is_cf_challenge = (
                resp.status_code == 403 or
                "challenges.cloudflare.com" in resp.text or
                "Cf-Mitigated" in resp.headers or
                "Just a moment..." in resp.text
            )

            if is_cf_challenge:
                error_msg = f"HTTP {resp.status_code}: Cloudflare Bot Management / Challenge detected"
                URLRepository.mark_failed(
                    db, url_record.id, error_msg=error_msg,
                    is_retryable=False, http_status=resp.status_code, is_inaccessible=True
                )
                JobRepository.log_error(
                    db, job_id, url_record.url, stage="fetch",
                    error_type="ACCESS_RESTRICTED", error_message=error_msg, is_retryable=False
                )
                return {"status": "inaccessible", "http_status": resp.status_code}

            if resp.status_code != 200:
                error_msg = f"HTTP {resp.status_code} Error"
                is_retry = resp.status_code in (429, 500, 502, 503, 504)
                URLRepository.mark_failed(
                    db, url_record.id, error_msg=error_msg,
                    is_retryable=is_retry, http_status=resp.status_code
                )
                JobRepository.log_error(
                    db, job_id, url_record.url, stage="fetch",
                    error_type=f"HTTP_{resp.status_code}", error_message=error_msg, is_retryable=is_retry
                )
                return {"status": "failed", "http_status": resp.status_code}

            # 200 OK Response: Save snapshot to disk before parsing
            html = resp.text
            effective_url = str(resp.url)
            http_status = resp.status_code
            raw_store.save(url_record.url, html, status_code=http_status, final_url=effective_url)

        # Successful HTML available: Parse according to URL type or page content
        soup = BeautifulSoup(html, "lxml")
        url_type = url_record.url_type
        is_product = (
            url_type == URLType.PRODUCT.value or
            url_record.url.lower().endswith(".html") or
            bool(soup.find("meta", property="og:type", content=lambda v: v and "product" in v.lower())) or
            bool(soup.find(attrs={"itemtype": lambda v: v and "Product" in v})) or
            bool(soup.select_one(".product-info-main"))
        )

        try:
            if is_product:
                prod_create = extract_product_detail(html, effective_url)
                if prod_create:
                    prod_create.crawl_job_id = job_id
                    prod, is_new = ProductRepository.upsert_product(db, prod_create)
                    if is_new:
                        JobRepository.increment_product_count(db, job_id, 1)

            else:
                # Listing, Category, Manufacturer, or Search page
                # 1. Discover subcategories if on category page
                new_cats = extract_category_tree(soup, effective_url)
                for cat_create in new_cats:
                    CategoryRepository.upsert_category(db, cat_create)
                    URLRepository.enqueue_url(
                        db, job_id, cat_create.source_url, depth=url_record.depth + 1, forced_type=URLType.CATEGORY
                    )

                # 2. Discover pagination URLs
                curr_p, total_p, page_urls = extract_pagination(soup, effective_url)
                for p_url in page_urls:
                    URLRepository.enqueue_url(
                        db, job_id, p_url, depth=url_record.depth + 1, forced_type=URLType.PAGINATION
                    )

                # 3. Discover product detail URLs
                prod_urls = extract_listing_products(soup, effective_url)
                for pr_url in prod_urls:
                    URLRepository.enqueue_url(
                        db, job_id, pr_url, depth=url_record.depth + 1, forced_type=URLType.PRODUCT
                    )

            # Mark processed
            URLRepository.mark_processed(db, url_record.id, http_status=200)
            return {"status": "processed", "http_status": 200}

        except Exception as e:
            URLRepository.mark_failed(
                db, url_record.id, error_msg=f"Parse error: {e}", is_retryable=False, http_status=200
            )
            JobRepository.log_error(
                db, job_id, url_record.url, stage="parse",
                error_type="PARSE_ERROR", error_message=str(e), is_retryable=False
            )
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def run_job_batch(db: Session, job_id: int, worker_id: str = "worker-1", batch_size: int = 10) -> int:
        """Claim and process a batch of URLs for a job."""
        job = JobRepository.get_job(db, job_id)
        if not job or job.status in (JobStatus.PAUSED.value, JobStatus.CANCELLED.value, JobStatus.COMPLETED.value):
            return 0

        if job.status == JobStatus.QUEUED.value:
            JobRepository.update_status(db, job_id, JobStatus.RUNNING)

        claimed = URLRepository.claim_urls(db, job_id, worker_id=worker_id, batch_size=batch_size)
        if not claimed:
            # Check if any remaining URLs are in_progress or queued
            progress = JobRepository.get_progress(db, job_id)
            if progress and (progress.urls_queued == 0 and progress.urls_in_progress == 0):
                final_status = JobStatus.COMPLETED_WITH_ERRORS if (progress.urls_failed_terminal > 0 or progress.urls_inaccessible > 0) else JobStatus.COMPLETED
                JobRepository.update_status(db, job_id, final_status)
            return 0

        for url_rec in claimed:
            JobRunner.process_url(db, job_id, url_rec)

        db.commit()
        return len(claimed)
