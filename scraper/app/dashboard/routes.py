"""Server-rendered dashboard routes using Jinja2 templates and HTMX."""
import os
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import update, and_
from app.api.dependencies import get_db
from app.database.models.url import CrawlURL
from app.schemas.job import JobScope, JobStatus
from app.schemas.crawl import URLStatus
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.category_repo import CategoryRepository
from app.database.repositories.url_repo import URLRepository
from app.services.coverage import (
    get_overview_report, get_coverage_report,
    get_completeness_report, get_error_report
)
from app.services.discovery import init_job_seeds
from app.services.job_runner import JobRunner
from app.services.dispatcher import JobDispatcher

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard_overview(request: Request, db: Session = Depends(get_db)):
    """Overview dashboard page."""
    overview = get_overview_report(db)
    recent_jobs = JobRepository.list_jobs(db, skip=0, limit=5)
    return templates.TemplateResponse(
        request=request,
        name="overview.html",
        context={
            "request": request,
            "active_page": "overview",
            "overview": overview,
            "recent_jobs": recent_jobs
        }
    )


@router.get("/jobs", response_class=HTMLResponse)
def dashboard_jobs(request: Request, db: Session = Depends(get_db)):
    """Scraping jobs management page."""
    jobs = JobRepository.list_jobs(db, skip=0, limit=50)
    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "request": request,
            "active_page": "jobs",
            "jobs": jobs
        }
    )


@router.post("/jobs/start")
def dashboard_start_job(
    background_tasks: BackgroundTasks,
    scope: str = Form("full"),
    seed_url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Start a crawl job from dashboard form."""
    custom_seeds = [seed_url.strip()] if seed_url and seed_url.strip() else None
    job = JobRepository.create_job(db, scope=JobScope(scope))
    init_job_seeds(db, job.id, custom_seeds=custom_seeds)
    db.commit()
    JobDispatcher.dispatch_job(job.id, background_tasks=background_tasks)
    return RedirectResponse(url=f"/dashboard/jobs/{job.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/jobs/{job_id}/run-batch")
def dashboard_run_batch(job_id: int, db: Session = Depends(get_db)):
    """Manually process one batch of URLs for immediate feedback."""
    JobRunner.run_job_batch(db, job_id=job_id, batch_size=10)
    return RedirectResponse(url=f"/dashboard/jobs/{job_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/jobs/{job_id}/dispatch")
def dashboard_dispatch_job(job_id: int, background_tasks: BackgroundTasks):
    """Trigger background execution for an existing queued or running job."""
    JobDispatcher.dispatch_job(job_id, background_tasks=background_tasks)
    return RedirectResponse(url=f"/dashboard/jobs/{job_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def dashboard_job_detail(job_id: int, request: Request, db: Session = Depends(get_db)):
    """Inspect progress and URL breakdown of a job."""
    job = JobRepository.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    prog = JobRepository.get_progress(db, job_id)
    errors = JobRepository.get_job_errors(db, job_id, limit=20)
    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={
            "request": request,
            "active_page": "jobs",
            "job": job,
            "progress": prog,
            "errors": errors
        }
    )


@router.post("/jobs/{job_id}/pause")
def dashboard_pause_job(job_id: int, db: Session = Depends(get_db)):
    JobRepository.update_status(db, job_id, JobStatus.PAUSED)
    db.commit()
    return RedirectResponse(url=f"/dashboard/jobs/{job_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/jobs/{job_id}/resume")
def dashboard_resume_job(job_id: int, db: Session = Depends(get_db)):
    JobRepository.update_status(db, job_id, JobStatus.RUNNING)
    db.commit()
    return RedirectResponse(url=f"/dashboard/jobs/{job_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/jobs/{job_id}/cancel")
def dashboard_cancel_job(job_id: int, db: Session = Depends(get_db)):
    JobRepository.update_status(db, job_id, JobStatus.CANCELLED)
    db.commit()
    return RedirectResponse(url=f"/dashboard/jobs/{job_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/products", response_class=HTMLResponse)
def dashboard_products(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = None,
    brand: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Browse products catalogue."""
    page_size = 30
    items, total = ProductRepository.list_products(
        db, page=page, page_size=page_size, search=search, brand=brand
    )
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={
            "request": request,
            "active_page": "products",
            "products": items,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "search": search,
            "brand": brand
        }
    )


@router.get("/products/{product_id}", response_class=HTMLResponse)
def dashboard_product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    """View detailed product page with source language, translation, specs, and provenance."""
    prod = ProductRepository.get_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse(
        request=request,
        name="product_detail.html",
        context={
            "request": request,
            "active_page": "products",
            "product": prod
        }
    )


@router.get("/categories", response_class=HTMLResponse)
def dashboard_categories(request: Request, db: Session = Depends(get_db)):
    """Browse hierarchical category tree."""
    cats = CategoryRepository.list_categories(db, limit=200)
    cov = CategoryRepository.get_coverage(db)
    return templates.TemplateResponse(
        request=request,
        name="categories.html",
        context={
            "request": request,
            "active_page": "categories",
            "categories": cats,
            "coverage": cov
        }
    )


@router.get("/failures", response_class=HTMLResponse)
def dashboard_failures(request: Request, db: Session = Depends(get_db)):
    """View failed & inaccessible URLs."""
    from sqlalchemy import select
    stmt = select(CrawlURL).where(
        CrawlURL.status.in_([
            URLStatus.FAILED_RETRYABLE.value,
            URLStatus.FAILED_TERMINAL.value,
            URLStatus.INACCESSIBLE.value
        ])
    ).order_by(CrawlURL.updated_at.desc()).limit(100)
    failed = list(db.execute(stmt).scalars().all())
    return templates.TemplateResponse(
        request=request,
        name="failures.html",
        context={
            "request": request,
            "active_page": "failures",
            "failed_urls": failed
        }
    )


@router.post("/failures/retry-all")
def dashboard_retry_all_failures(db: Session = Depends(get_db)):
    db.execute(
        update(CrawlURL)
        .where(CrawlURL.status == URLStatus.FAILED_RETRYABLE.value)
        .values(status=URLStatus.QUEUED.value, lease_id=None, lease_expires_at=None)
    )
    db.commit()
    return RedirectResponse(url="/dashboard/failures", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/failures/retry/{url_id}")
def dashboard_retry_single_url(url_id: int, db: Session = Depends(get_db)):
    url_rec = db.get(CrawlURL, url_id)
    if url_rec:
        url_rec.status = URLStatus.QUEUED.value
        url_rec.attempts = 0
        url_rec.lease_id = None
        url_rec.lease_expires_at = None
        db.commit()
    return RedirectResponse(url="/dashboard/failures", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reports", response_class=HTMLResponse)
def dashboard_reports(request: Request, db: Session = Depends(get_db)):
    """View data quality, coverage and error reports."""
    cov = get_coverage_report(db)
    comp = get_completeness_report(db)
    err = get_error_report(db)
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "request": request,
            "active_page": "reports",
            "coverage": cov,
            "completeness": comp,
            "errors": err
        }
    )
