"""Scraping control and dispatch API endpoints."""
from typing import List, Optional
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.job import JobScope, JobStatus, CrawlJobResponse, CrawlJobCreate
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.database.repositories.category_repo import CategoryRepository
from app.database.repositories.manufacturer_repo import ManufacturerRepository
from app.services.discovery import init_job_seeds
from app.services.coverage import get_overview_report
from app.services.dispatcher import JobDispatcher
from app.services.raw_store import raw_store
from app.services.job_runner import JobRunner

router = APIRouter(prefix="/scraping", tags=["Scraping Control"])


class URLListPayload(BaseModel):
    urls: List[str]


class HTMLIngestPayload(BaseModel):
    url: str
    html: str
    final_url: Optional[str] = None


@router.post("/start", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_scraping_job(
    background_tasks: BackgroundTasks,
    payload: CrawlJobCreate = CrawlJobCreate(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Start a full or customized scraping job."""
    job = JobRepository.create_job(db, scope=payload.scope, config=payload.model_dump())
    init_job_seeds(db, job.id, custom_seeds=payload.seed_urls)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message="Scraping job queued and dispatched successfully",
        data={"job_id": job.id, "status": job.status, "scope": job.scope}
    )


@router.post("/start/category", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_category_scraping(
    background_tasks: BackgroundTasks,
    category_id: int = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape a selected category."""
    cat = CategoryRepository.get_by_id(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    job = JobRepository.create_job(
        db, scope=JobScope.CATEGORY, config={"category_id": cat.id, "url": cat.source_url}
    )
    URLRepository.enqueue_url(db, job.id, cat.source_url)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Category scraping queued for '{cat.name}'",
        data={"job_id": job.id, "category_id": cat.id}
    )


@router.post("/start/manufacturer", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_manufacturer_scraping(
    background_tasks: BackgroundTasks,
    manufacturer_id: int = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape a selected manufacturer."""
    man = ManufacturerRepository.get_by_id(db, manufacturer_id)
    if not man or not man.source_url:
        raise HTTPException(status_code=404, detail="Manufacturer not found or missing source URL")

    job = JobRepository.create_job(
        db, scope=JobScope.MANUFACTURER, config={"manufacturer_id": man.id, "url": man.source_url}
    )
    URLRepository.enqueue_url(db, job.id, man.source_url)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Manufacturer scraping queued for '{man.name}'",
        data={"job_id": job.id, "manufacturer_id": man.id}
    )


@router.post("/start/search", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_search_scraping(
    background_tasks: BackgroundTasks,
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape search results for a keyword."""
    encoded_q = quote_plus(query)
    search_url = f"https://www.audiovideo.lt/catalogsearch/result/?cat=0&q={encoded_q}"
    job = JobRepository.create_job(db, scope=JobScope.SEARCH, config={"query": query, "url": search_url})
    URLRepository.enqueue_url(db, job.id, search_url)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Search scraping queued for '{query}'",
        data={"job_id": job.id, "query": query}
    )


@router.post("/start/urls", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_urls_scraping(
    background_tasks: BackgroundTasks,
    payload: URLListPayload,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Scrape a supplied list of URLs."""
    if not payload.urls:
        raise HTTPException(status_code=400, detail="URL list must not be empty")

    job = JobRepository.create_job(db, scope=JobScope.CUSTOM_URLS, config={"urls_count": len(payload.urls)})
    enqueued = URLRepository.enqueue_batch(db, job.id, payload.urls)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return APIResponse(
        success=True,
        message=f"Custom URLs scraping queued ({enqueued} valid URLs enqueued)",
        data={"job_id": job.id, "enqueued_count": enqueued}
    )


@router.post("/ingest-html", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
def ingest_html_payload(
    payload: HTMLIngestPayload,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Ingest and cache raw HTML for a URL, then immediately parse it into the database."""
    raw_store.save(payload.url, payload.html, status_code=200, final_url=payload.final_url)
    job = JobRepository.create_job(db, scope=JobScope.CUSTOM_URLS, config={"source": "api_html_ingest"})
    crawl_url = URLRepository.enqueue_url(db, job.id, payload.url)
    db.commit()
    if crawl_url:
        JobRunner.process_url(db, job.id, crawl_url)
        db.commit()
    return APIResponse(
        success=True,
        message=f"Raw HTML snapshot saved and parsed for '{payload.url}'",
        data={"url": payload.url, "job_id": job.id}
    )


@router.post("/pause/{job_id}", response_model=APIResponse[dict])
def pause_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Pause an active job."""
    job = JobRepository.update_status(db, job_id, JobStatus.PAUSED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.commit()
    return APIResponse(success=True, message=f"Job {job_id} paused", data={"status": job.status})


@router.post("/resume/{job_id}", response_model=APIResponse[dict])
def resume_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Resume a paused job."""
    job = JobRepository.update_status(db, job_id, JobStatus.RUNNING)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.commit()
    return APIResponse(success=True, message=f"Job {job_id} resumed", data={"status": job.status})


@router.post("/cancel/{job_id}", response_model=APIResponse[dict])
def cancel_job(job_id: int, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Cancel a job."""
    job = JobRepository.update_status(db, job_id, JobStatus.CANCELLED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.commit()
    return APIResponse(success=True, message=f"Job {job_id} cancelled", data={"status": job.status})


@router.get("/status", response_model=APIResponse[dict])
def get_current_scraping_status(db: Session = Depends(get_db)):
    """Get current scraping overview status."""
    overview = get_overview_report(db)
    return APIResponse(
        success=True,
        message="Current scraping status retrieved",
        data={
            "active_jobs": overview.active_jobs,
            "completed_jobs": overview.completed_jobs,
            "total_products_collected": overview.total_products,
            "processed_urls": overview.total_urls_processed,
            "failed_urls": overview.total_urls_failed,
            "inaccessible_urls": overview.total_urls_inaccessible
        }
    )


@router.get("/history", response_model=APIResponse[List[CrawlJobResponse]])
def get_scraping_history(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Get previous scraping runs and jobs."""
    jobs = JobRepository.list_jobs(db, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Scraping history retrieved",
        data=[CrawlJobResponse.model_validate(j) for j in jobs]
    )
