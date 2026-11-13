"""Category Pydantic schemas."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(..., description="Lithuanian source category name")
    slug: str = Field(..., description="Category URL slug")
    source_url: str = Field(..., description="Source page URL")
    parent_id: Optional[int] = Field(default=None, description="Parent category ID if nested")
    level: int = Field(default=0, description="Nesting level (0 = root)")
    is_leaf: bool = Field(default=False, description="Whether this is a leaf category")
    product_count_observed: int = Field(default=0, description="Total unique products extracted in this category")
    product_count_source: Optional[int] = Field(default=None, description="Reported product count if published on site")


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryTreeNode(CategoryResponse):
    children: List["CategoryTreeNode"] = Field(default_factory=list)


class CategoryCoverageResponse(BaseModel):
    total_categories_discovered: int
    root_categories: int
    subcategories: int
    leaf_categories: int
    categories_with_products: int
    coverage_percentage: float = Field(..., description="Percentage of discovered categories that have extracted products")
