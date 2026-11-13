"""Manufacturer Pydantic schemas."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ManufacturerBase(BaseModel):
    name: str = Field(..., description="Brand / manufacturer name")
    slug: str = Field(..., description="Manufacturer URL slug")
    source_url: Optional[str] = Field(default=None, description="Manufacturer listing URL")
    product_count_observed: int = Field(default=0, description="Observed unique products count")
    product_count_source: Optional[int] = Field(default=None, description="Source reported count if available")


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerResponse(ManufacturerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManufacturerCoverageResponse(BaseModel):
    total_manufacturers: int
    manufacturers_with_products: int
    coverage_percentage: float = Field(..., description="Percentage of manufacturers with extracted products")
