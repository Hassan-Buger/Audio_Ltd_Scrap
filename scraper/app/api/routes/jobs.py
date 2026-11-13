"""Jobs and durable crawl management API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, update
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.job import CrawlJobResponse, CrawlJobProgressResponse, CrawlJobErrorItem
from app.schemas.crawl import CrawlURLResponse, CrawlFailedURLResponse, URLStatus
from app.schemas.product import ProductResponse
from app.database.models.url import CrawlURL
from app.database.models.product import Product
from app.database.models.job import ScrapeError
from app.database.repositories.job_repo import JobRepository

router = APIRouter(tags=["Jobs & Crawl Management"])


@router.get("/jobs", response_model=APIResponse[List[CrawlJobResponse]])
def list_jobs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List scraping jobs."""
    jobs = JobRepository.list_jobs(db, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Jobs list retrieved",
        data=[CrawlJobResponse.model_validate(j) for j in jobs]
    )


@router.get("/jobs/{job_id}", response_model=APIResponse[CrawlJobResponse])
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Get job details."""
    job = JobRepository.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(
        success=True,
        message="Job detail retrieved",
        data=CrawlJobResponse.model_validate(job)
    )


@router.get("/jobs/{job_id}/progress", response_model=APIResponse[CrawlJobProgressResponse])
def get_job_progress(job_id: int, db: Session = Depends(get_db)):
    """Get real-time job progress and URL breakdown."""
    prog = JobRepository.get_progress(db, job_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(
        success=True,
        message="Job progress retrieved",
        data=prog
    )


@router.get("/jobs/{job_id}/errors", response_model=APIResponse[List[CrawlJobErrorItem]])
def get_job_errors(job_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get errors recorded for a job."""
    errors = JobRepository.get_job_errors(db, job_id, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Job errors retrieved",
        data=errors
    )


@router.get("/jobs/{job_id}/results", response_model=APIResponse[List[ProductResponse]])
def get_job_results(
    job_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get products extracted by a specific job."""
    from app.database.models.url import ProductSource
    stmt = (
        select(Product)
        .join(ProductSource, ProductSource.product_id == Product.id)
        .where(ProductSource.crawl_job_id == job_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.execute(stmt).scalars().all())
    return APIResponse(
        success=True,
        message="Job products retrieved",
        data=[ProductResponse.model_validate(p) for p in items]
    )


@router.get("/crawl/queue", response_model=APIResponse[List[CrawlURLResponse]])
def inspect_crawl_queue(
    job_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Inspect pending crawl URLs in the durable frontier."""
    stmt = select(CrawlURL).where(CrawlURL.status == URLStatus.QUEUED.value)
    if job_id is not None:
        stmt = stmt.where(CrawlURL.crawl_job_id == job_id)
    stmt = stmt.order_by(CrawlURL.depth.asc(), CrawlURL.id.asc()).offset(skip).limit(limit)
    urls = list(db.execute(stmt).scalars().all())
    return APIResponse(
        success=True,
        message="Frontier queue retrieved",
        data=[CrawlURLResponse.model_validate(u) for u in urls]
    )


@router.get("/crawl/failed", response_model=APIResponse[List[CrawlFailedURLResponse]])
def list_failed_urls(
    job_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List failed and inaccessible URLs."""
    stmt = select(CrawlURL).where(
        CrawlURL.status.in_([
            URLStatus.FAILED_RETRYABLE.value,
            URLStatus.FAILED_TERMINAL.value,
            URLStatus.INACCESSIBLE.value
        ])
    )
    if job_id is not None:
        stmt = stmt.where(CrawlURL.crawl_job_id == job_id)
    stmt = stmt.order_by(CrawlURL.updated_at.desc()).offset(skip).limit(limit)
    urls = list(db.execute(stmt).scalars().all())

    return APIResponse(
        success=True,
        message="Failed URLs retrieved",
        data=[
            CrawlFailedURLResponse(
                id=u.id,
                crawl_job_id=u.crawl_job_id,
                url=u.url,
                url_type=u.url_type,
                status=u.status,
                attempts=u.attempts,
                last_error=u.last_error,
                http_status=u.http_status,
                is_retryable=u.status == URLStatus.FAILED_RETRYABLE.value,
                updated_at=u.updated_at
            )
            for u in urls
        ]
    )


@router.post("/crawl/retry-failed", response_model=APIResponse[dict])
def retry_failed_urls(
    job_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Retry all eligible failed URLs by resetting them to queued."""
    conditions = [CrawlURL.status == URLStatus.FAILED_RETRYABLE.value]
    if job_id is not None:
        conditions.append(CrawlURL.crawl_job_id == job_id)

    result = db.execute(
        update(CrawlURL)
        .where(and_(*conditions))
        .values(status=URLStatus.QUEUED.value, lease_id=None, lease_expires_at=None)
    )
    db.commit()
    return APIResponse(
        success=True,
        message=f"Reset {result.rowcount} failed URLs to queued",
        data={"retried_count": result.rowcount}
    )


@router.post("/crawl/retry/{url_id}", response_model=APIResponse[dict])
def retry_single_url(
    url_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Retry a specific failed URL."""
    url_rec = db.get(CrawlURL, url_id)
    if not url_rec:
        raise HTTPException(status_code=404, detail="URL not found")

    url_rec.status = URLStatus.QUEUED.value
    url_rec.attempts = 0
    url_rec.lease_id = None
    url_rec.lease_expires_at = None
    db.commit()

    return APIResponse(
        success=True,
        message=f"URL {url_id} reset to queued for retry",
        data={"url_id": url_id, "url": url_rec.url}
    )
