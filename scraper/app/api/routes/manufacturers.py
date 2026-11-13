"""Manufacturers API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.manufacturer import ManufacturerResponse, ManufacturerCoverageResponse
from app.schemas.product import ProductResponse
from app.database.repositories.manufacturer_repo import ManufacturerRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.schemas.job import JobScope

router = APIRouter(prefix="/manufacturers", tags=["Manufacturers"])


@router.get("", response_model=APIResponse[List[ManufacturerResponse]])
def list_manufacturers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List manufacturers."""
    mans = ManufacturerRepository.list_manufacturers(db, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Manufacturers retrieved",
        data=[ManufacturerResponse.model_validate(m) for m in mans]
    )


@router.get("/coverage", response_model=APIResponse[ManufacturerCoverageResponse])
def get_manufacturer_coverage(db: Session = Depends(get_db)):
    """Manufacturer scraping coverage."""
    cov = ManufacturerRepository.get_coverage(db)
    return APIResponse(
        success=True,
        message="Manufacturer coverage calculated",
        data=cov
    )


@router.get("/{manufacturer_id}", response_model=APIResponse[ManufacturerResponse])
def get_manufacturer(manufacturer_id: int, db: Session = Depends(get_db)):
    """Get manufacturer details."""
    man = ManufacturerRepository.get_by_id(db, manufacturer_id)
    if not man:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Manufacturer {manufacturer_id} not found"}
        )
    return APIResponse(
        success=True,
        message="Manufacturer retrieved",
        data=ManufacturerResponse.model_validate(man)
    )


@router.get("/{manufacturer_id}/products", response_model=APIResponse[List[ProductResponse]])
def get_manufacturer_products(
    manufacturer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get manufacturer products."""
    items, total = ProductRepository.list_products(
        db, page=page, page_size=page_size, manufacturer_id=manufacturer_id
    )
    return APIResponse(
        success=True,
        message="Manufacturer products retrieved",
        data=[ProductResponse.model_validate(p) for p in items]
    )


@router.post("/discover", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def discover_manufacturers(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Discover manufacturer pages and start scraping."""
    job = JobRepository.create_job(db, scope=JobScope.MANUFACTURER)
    URLRepository.enqueue_url(db, job.id, "https://www.audiovideo.lt/gamintojai/hertz")
    db.commit()
    return APIResponse(
        success=True,
        message="Manufacturer crawl initiated",
        data={"job_id": job.id, "scope": job.scope}
    )
