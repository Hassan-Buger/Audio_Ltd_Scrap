"""Translation Pydantic schemas."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TranslationStatusResponse(BaseModel):
    enabled: bool
    provider: str
    total_products: int
    translated_products: int
    pending_products: int
    failed_translations: int
    coverage_percentage: float


class TranslationRequest(BaseModel):
    product_ids: Optional[List[int]] = Field(default=None, description="Optional specific product IDs to translate")
    target_language: str = Field(default="en", description="Target ISO language code")
