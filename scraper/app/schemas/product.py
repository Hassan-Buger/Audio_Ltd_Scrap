"""Product Pydantic schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class SpecificationItem(BaseModel):
    label: str = Field(..., description="Lithuanian specification key/label")
    value: str = Field(..., description="Original raw specification text value")
    numeric_value: Optional[Decimal] = Field(default=None, description="Parsed numeric value if present")
    unit: Optional[str] = Field(default=None, description="Parsed unit if present")

    model_config = {"from_attributes": True}


class ProductTranslationSchema(BaseModel):
    id: Optional[int] = None
    language: str = Field(default="en", description="Target language code")
    title: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductSourceSchema(BaseModel):
    id: Optional[int] = None
    source_url: str
    discovery_type: str = Field(..., description="category, manufacturer, search, direct")
    crawl_job_id: Optional[int] = None
    discovered_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductBase(BaseModel):
    canonical_url: str = Field(..., description="Canonical product detail URL")
    title: str = Field(..., description="Original Lithuanian product title")
    sku: Optional[str] = Field(default=None, description="Product SKU code")
    ean: Optional[str] = Field(default=None, description="EAN/GTIN barcode")
    model: Optional[str] = Field(default=None, description="Model identifier")
    manufacturer_id: Optional[int] = Field(default=None, description="Manufacturer ID")
    brand_name: Optional[str] = Field(default=None, description="Extracted brand name")
    
    price: Optional[Decimal] = Field(default=None, description="Current price in EUR")
    regular_price: Optional[Decimal] = Field(default=None, description="Original/strikethrough price if discounted")
    currency: str = Field(default="EUR", description="Currency symbol/code")
    availability: Optional[str] = Field(default=None, description="Source availability text in Lithuanian")
    in_stock: Optional[bool] = Field(default=None, description="Normalized in-stock flag")
    
    description: Optional[str] = Field(default=None, description="Original Lithuanian product description")
    images: List[str] = Field(default_factory=list, description="List of product image URLs")
    is_complete: bool = Field(default=False, description="Whether core identity fields (title, price, sku/url) are present")


class ProductCreate(ProductBase):
    specifications: List[SpecificationItem] = Field(default_factory=list)
    category_ids: List[int] = Field(default_factory=list)
    source_url: Optional[str] = None
    discovery_type: str = "direct"
    crawl_job_id: Optional[int] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    sku: Optional[str] = None
    ean: Optional[str] = None
    model: Optional[str] = None
    price: Optional[Decimal] = None
    regular_price: Optional[Decimal] = None
    availability: Optional[str] = None
    in_stock: Optional[bool] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_complete: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # WooCommerce-compatible Aliases and Enriched Fields
    source_id: Optional[str] = Field(default=None, description="External/WooCommerce entity ID")
    source_url: Optional[str] = Field(default=None, description="Canonical source page URL")
    brand: Optional[str] = Field(default=None, description="Brand name alias")
    category_name: Optional[str] = Field(default=None, description="Primary category name")
    category_slug: Optional[str] = Field(default=None, description="Primary category slug")
    title_en: Optional[str] = Field(default=None, description="English translated title if available")
    sale_price: Optional[float] = Field(default=None, description="Discounted price if on sale")
    specifications: List[SpecificationItem] = Field(default_factory=list, description="Structured key-value specifications")

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductResponse):
    category_names: List[str] = Field(default_factory=list)
    sources: List[ProductSourceSchema] = Field(default_factory=list)
    translations: List[ProductTranslationSchema] = Field(default_factory=list)
