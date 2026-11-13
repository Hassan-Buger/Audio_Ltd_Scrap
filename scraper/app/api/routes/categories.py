"""Categories API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.category import CategoryResponse, CategoryTreeNode, CategoryCoverageResponse
from app.schemas.product import ProductResponse
from app.database.repositories.category_repo import CategoryRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.schemas.job import JobScope

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=APIResponse[List[CategoryResponse]])
def list_categories(
    parent_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List categories, optionally filtering by parent_id."""
    cats = CategoryRepository.list_categories(db, parent_id=parent_id, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Categories retrieved successfully",
        data=[CategoryResponse.model_validate(c) for c in cats]
    )


@router.get("/tree", response_model=APIResponse[List[CategoryTreeNode]])
def get_category_tree(db: Session = Depends(get_db)):
    """Get complete hierarchical category tree (parent, child, nested)."""
    tree = CategoryRepository.get_tree(db)
    return APIResponse(
        success=True,
        message="Category tree retrieved successfully",
        data=tree
    )


@router.get("/coverage", response_model=APIResponse[CategoryCoverageResponse])
def get_category_coverage(db: Session = Depends(get_db)):
    """Compare discovered and scraped category coverage."""
    cov = CategoryRepository.get_coverage(db)
    return APIResponse(
        success=True,
        message="Category coverage calculated",
        data=cov
    )


@router.get("/{category_id}", response_model=APIResponse[CategoryResponse])
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category details."""
    cat = CategoryRepository.get_by_id(db, category_id)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Category {category_id} not found"}
        )
    return APIResponse(
        success=True,
        message="Category retrieved",
        data=CategoryResponse.model_validate(cat)
    )


@router.get("/{category_id}/children", response_model=APIResponse[List[CategoryResponse]])
def get_category_children(category_id: int, db: Session = Depends(get_db)):
    """Get direct child categories."""
    children = CategoryRepository.get_children(db, category_id)
    return APIResponse(
        success=True,
        message="Child categories retrieved",
        data=[CategoryResponse.model_validate(c) for c in children]
    )


@router.get("/{category_id}/products", response_model=APIResponse[List[ProductResponse]])
def get_category_products(
    category_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get products in a category."""
    items, total = ProductRepository.list_products(db, page=page, page_size=page_size, category_id=category_id)
    return APIResponse(
        success=True,
        message="Category products retrieved",
        data=[ProductResponse.model_validate(p) for p in items]
    )


@router.post("/discover", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def discover_categories(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Start recursive category discovery job."""
    job = JobRepository.create_job(db, scope=JobScope.CATEGORY)
    # Seed with the category seed
    URLRepository.enqueue_url(
        db, job.id, "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1"
    )
    db.commit()
    return APIResponse(
        success=True,
        message="Category discovery job initiated",
        data={"job_id": job.id, "scope": job.scope}
    )
