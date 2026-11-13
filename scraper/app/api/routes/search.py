"""Search API endpoints."""
from typing import List, Optional
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.product import ProductResponse
from app.schemas.category import CategoryResponse
from app.schemas.manufacturer import ManufacturerResponse
from app.database.models.category import Category
from app.database.models.manufacturer import Manufacturer
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.schemas.job import JobScope

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/products", response_model=APIResponse[List[ProductResponse]])
def search_products(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Search extracted products by keyword across title, SKU, EAN, brand, and description."""
    items, total = ProductRepository.list_products(db, page=page, page_size=page_size, search=q)
    return APIResponse(
        success=True,
        message=f"Found {total} products matching '{q}'",
        data=[ProductResponse.model_validate(p) for p in items]
    )


@router.get("/categories", response_model=APIResponse[List[CategoryResponse]])
def search_categories(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Search categories by name or slug."""
    kw = f"%{q}%"
    stmt = select(Category).where(Category.name.ilike(kw) | Category.slug.ilike(kw))
    cats = list(db.execute(stmt).scalars().all())
    return APIResponse(
        success=True,
        message="Categories matching query retrieved",
        data=[CategoryResponse.model_validate(c) for c in cats]
    )


@router.get("/manufacturers", response_model=APIResponse[List[ManufacturerResponse]])
def search_manufacturers(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Search manufacturers by name."""
    kw = f"%{q}%"
    stmt = select(Manufacturer).where(Manufacturer.name.ilike(kw))
    mans = list(db.execute(stmt).scalars().all())
    return APIResponse(
        success=True,
        message="Manufacturers matching query retrieved",
        data=[ManufacturerResponse.model_validate(m) for m in mans]
    )


@router.post("/scrape", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def search_and_scrape(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Search source website and enqueue search result page for crawling."""
    encoded_q = quote_plus(q)
    search_url = f"https://www.audiovideo.lt/catalogsearch/result/?cat=0&q={encoded_q}"
    job = JobRepository.create_job(db, scope=JobScope.SEARCH, config={"query": q, "url": search_url})
    URLRepository.enqueue_url(db, job.id, search_url)
    db.commit()
    return APIResponse(
        success=True,
        message=f"Search crawl job enqueued for '{q}'",
        data={"job_id": job.id, "search_url": search_url}
    )
