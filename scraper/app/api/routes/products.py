"""Product catalogue API endpoints."""
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.product import (
    ProductResponse, ProductDetailResponse, ProductCreate,
    ProductUpdate, SpecificationItem, ProductSourceSchema, ProductTranslationSchema
)
from app.database.repositories.product_repo import ProductRepository

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=APIResponse[List[ProductResponse]])
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    sku: Optional[str] = None,
    ean: Optional[str] = None,
    brand: Optional[str] = None,
    category_id: Optional[int] = None,
    manufacturer_id: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    sort_by: str = Query("id", pattern="^(id|title|price|sku|brand_name|created_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """List products with pagination, search and filtering."""
    items, total = ProductRepository.list_products(
        db, page=page, page_size=page_size, search=search, sku=sku,
        ean=ean, brand=brand, category_id=category_id, manufacturer_id=manufacturer_id,
        min_price=min_price, max_price=max_price, sort_by=sort_by, sort_order=sort_order
    )
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return APIResponse(
        success=True,
        message="Products retrieved successfully",
        data=[ProductResponse.model_validate(p) for p in items],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/sku/{sku}", response_model=APIResponse[ProductDetailResponse])
def get_product_by_sku(sku: str, db: Session = Depends(get_db)):
    """Find product by SKU."""
    prod = ProductRepository.get_by_sku(db, sku)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Product with SKU '{sku}' not found"}
        )
    return APIResponse(
        success=True,
        message="Product found",
        data=_format_product_detail(prod)
    )


@router.get("/ean/{ean}", response_model=APIResponse[ProductDetailResponse])
def get_product_by_ean(ean: str, db: Session = Depends(get_db)):
    """Find product by EAN/GTIN."""
    prod = ProductRepository.get_by_ean(db, ean)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Product with EAN '{ean}' not found"}
        )
    return APIResponse(
        success=True,
        message="Product found",
        data=_format_product_detail(prod)
    )


@router.get("/{product_id}", response_model=APIResponse[ProductDetailResponse])
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a product by ID."""
    prod = ProductRepository.get_by_id(db, product_id)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Product {product_id} not found"}
        )
    return APIResponse(
        success=True,
        message="Product retrieved successfully",
        data=_format_product_detail(prod)
    )


@router.get("/{product_id}/specifications", response_model=APIResponse[List[SpecificationItem]])
def get_specifications(product_id: int, db: Session = Depends(get_db)):
    """Get technical specifications for a product."""
    prod = ProductRepository.get_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    specs = [
        SpecificationItem(
            label=s.label, value=s.value, numeric_value=s.numeric_value, unit=s.unit
        )
        for s in prod.specifications
    ]
    return APIResponse(success=True, message="Specifications retrieved", data=specs)


@router.get("/{product_id}/categories", response_model=APIResponse[List[str]])
def get_categories(product_id: int, db: Session = Depends(get_db)):
    """Get associated category names for a product."""
    prod = ProductRepository.get_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return APIResponse(
        success=True, message="Categories retrieved",
        data=[c.name for c in prod.categories]
    )


@router.get("/{product_id}/sources", response_model=APIResponse[List[ProductSourceSchema]])
def get_sources(product_id: int, db: Session = Depends(get_db)):
    """Get discovery and provenance sources for a product."""
    prod = ProductRepository.get_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return APIResponse(
        success=True, message="Product sources retrieved",
        data=[ProductSourceSchema.model_validate(s) for s in prod.sources]
    )


@router.get("/{product_id}/translations", response_model=APIResponse[List[ProductTranslationSchema]])
def get_translations(product_id: int, db: Session = Depends(get_db)):
    """Get available translations for a product."""
    prod = ProductRepository.get_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return APIResponse(
        success=True, message="Translations retrieved",
        data=[ProductTranslationSchema.model_validate(t) for t in prod.translations]
    )


@router.post("", response_model=APIResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Create a new product record when authorized."""
    prod, _ = ProductRepository.upsert_product(db, payload)
    db.commit()
    db.refresh(prod)
    return APIResponse(
        success=True,
        message="Product created successfully",
        data=ProductResponse.model_validate(prod)
    )


@router.patch("/{product_id}", response_model=APIResponse[ProductResponse])
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Update permitted product fields when authorized."""
    prod = ProductRepository.update_product(db, product_id, payload)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
    db.refresh(prod)
    return APIResponse(
        success=True,
        message="Product updated successfully",
        data=ProductResponse.model_validate(prod)
    )


@router.delete("/{product_id}", response_model=APIResponse[dict])
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Delete a product when authorized."""
    success = ProductRepository.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
    return APIResponse(
        success=True,
        message="Product deleted successfully",
        data={"deleted_id": product_id}
    )


def _format_product_detail(prod) -> ProductDetailResponse:
    specs = [
        SpecificationItem(
            label=s.label, value=s.value, numeric_value=s.numeric_value, unit=s.unit
        )
        for s in prod.specifications
    ]
    sources = [
        ProductSourceSchema(
            id=s.id,
            source_url=s.source_url,
            discovery_type=s.discovery_type,
            crawl_job_id=s.crawl_job_id,
            discovered_at=s.discovered_at
        )
        for s in prod.sources
    ]
    translations = [
        ProductTranslationSchema(
            id=t.id,
            language=t.language,
            title=t.title,
            description=t.description,
            provider=t.provider,
            created_at=t.created_at
        )
        for t in prod.translations
    ]
    cats = [c.name for c in prod.categories]

    return ProductDetailResponse(
        id=prod.id,
        canonical_url=prod.canonical_url,
        title=prod.title,
        sku=prod.sku,
        ean=prod.ean,
        model=prod.model,
        manufacturer_id=prod.manufacturer_id,
        brand_name=prod.brand_name,
        price=prod.price,
        regular_price=prod.regular_price,
        currency=prod.currency,
        availability=prod.availability,
        in_stock=prod.in_stock,
        description=prod.description,
        images=prod.images,
        is_complete=prod.is_complete,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
        specifications=specs,
        category_names=cats,
        sources=sources,
        translations=translations
    )
