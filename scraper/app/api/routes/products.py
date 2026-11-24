"""Product catalogue API endpoints."""
from typing import Optional, List, Dict, Any
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
from app.api.routes.media import rewrite_image_url

router = APIRouter(prefix="/products", tags=["Products"])


def _format_product_data(prod) -> ProductResponse:
    """Format product model into WooCommerce-compatible ProductResponse with specifications and media URLs."""
    specs = [
        SpecificationItem(
            label=s.label,
            value=s.value,
            numeric_value=getattr(s, "numeric_value", None),
            unit=getattr(s, "unit", None)
        )
        if hasattr(s, "label") else SpecificationItem(**s)
        for s in (prod.specifications or [])
    ]
    rewritten_images = [rewrite_image_url(img) for img in (prod.images or [])]
    
    first_cat = prod.categories[0] if (hasattr(prod, "categories") and prod.categories) else None
    cat_name = first_cat.name if first_cat else (prod.brand_name or None)
    cat_slug = first_cat.slug if first_cat else (prod.brand_name.lower().replace(" ", "-") if prod.brand_name else None)
    
    title_en = None
    if hasattr(prod, "translations") and prod.translations:
        title_en = prod.translations[0].title
    if not title_en:
        title_en = prod.title

    avail = "in_stock" if prod.in_stock else ("out_of_stock" if prod.in_stock is False else (prod.availability or "in_stock"))
    sale_pr = float(prod.price) if (prod.regular_price and prod.price and prod.regular_price > prod.price) else None

    return ProductResponse(
        id=prod.id,
        source_id=str(prod.id),
        canonical_url=prod.canonical_url,
        source_url=prod.canonical_url,
        title=prod.title,
        title_en=title_en,
        sku=prod.sku,
        ean=prod.ean,
        model=prod.model,
        manufacturer_id=prod.manufacturer_id,
        brand_name=prod.brand_name,
        brand=prod.brand_name or (prod.manufacturer.name if prod.manufacturer else None),
        category_name=cat_name,
        category_slug=cat_slug,
        price=prod.price,
        regular_price=prod.regular_price,
        sale_price=sale_pr,
        currency=prod.currency or "EUR",
        availability=avail,
        in_stock=prod.in_stock,
        description=prod.description,
        images=rewritten_images,
        is_complete=prod.is_complete,
        specifications=specs,
        created_at=prod.created_at,
        updated_at=prod.updated_at
    )


@router.get("", response_model=APIResponse[List[ProductResponse]])
def list_products(
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=500),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Page limit (alias for page_size commonly used in WooCommerce)"),
    search: Optional[str] = None,
    sku: Optional[str] = None,
    ean: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = Query(None, description="Category slug or name (e.g. garso-izoliacija, hertz, audison, bass-habit)"),
    category_id: Optional[int] = None,
    manufacturer_id: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    sort_by: str = Query("id", pattern="^(id|title|price|sku|brand_name|created_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """List products with pagination, search, category filtering, specifications, and media proxy URLs."""
    eff_page_size = limit or page_size or 50
    items, total = ProductRepository.list_products(
        db, page=page, page_size=eff_page_size, search=search, sku=sku,
        ean=ean, brand=brand, category=category, category_id=category_id, manufacturer_id=manufacturer_id,
        min_price=min_price, max_price=max_price, sort_by=sort_by, sort_order=sort_order
    )
    total_pages = (total + eff_page_size - 1) // eff_page_size if eff_page_size > 0 else 0

    return APIResponse(
        success=True,
        message="Products retrieved successfully",
        data=[_format_product_data(p) for p in items],
        meta=PaginationMeta(
            page=page,
            page_size=eff_page_size,
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
        data=_format_product_data(prod)
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
        data=_format_product_data(prod)
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
            label=s.label,
            value=s.value,
            numeric_value=getattr(s, "numeric_value", None),
            unit=getattr(s, "unit", None)
        )
        if hasattr(s, "label") else SpecificationItem(**s)
        for s in (prod.specifications or [])
    ]
    sources = [
        ProductSourceSchema(
            id=s.id,
            source_url=s.source_url,
            discovery_type=s.discovery_type,
            crawl_job_id=s.crawl_job_id,
            discovered_at=s.discovered_at
        )
        for s in (prod.sources or [])
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
        for t in (prod.translations or [])
    ]
    cats = [c.name for c in (prod.categories or [])]
    first_cat = prod.categories[0] if (hasattr(prod, "categories") and prod.categories) else None
    cat_slug = first_cat.slug if first_cat else (prod.brand_name.lower().replace(" ", "-") if prod.brand_name else None)

    title_en = translations[0].title if translations else prod.title
    rewritten_images = [rewrite_image_url(img) for img in (prod.images or [])]
    avail = "in_stock" if prod.in_stock else ("out_of_stock" if prod.in_stock is False else (prod.availability or "in_stock"))
    sale_pr = float(prod.price) if (prod.regular_price and prod.price and prod.regular_price > prod.price) else None

    return ProductDetailResponse(
        id=prod.id,
        source_id=str(prod.id),
        canonical_url=prod.canonical_url,
        source_url=prod.canonical_url,
        title=prod.title,
        title_en=title_en,
        sku=prod.sku,
        ean=prod.ean,
        model=prod.model,
        manufacturer_id=prod.manufacturer_id,
        brand_name=prod.brand_name,
        brand=prod.brand_name or (prod.manufacturer.name if prod.manufacturer else None),
        category_name=cats[0] if cats else (prod.brand_name or None),
        category_slug=cat_slug,
        price=prod.price,
        regular_price=prod.regular_price,
        sale_price=sale_pr,
        currency=prod.currency or "EUR",
        availability=avail,
        in_stock=prod.in_stock,
        description=prod.description,
        images=rewritten_images,
        is_complete=prod.is_complete,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
        specifications=specs,
        category_names=cats,
        sources=sources,
        translations=translations
    )
