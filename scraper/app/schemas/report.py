"""Reports and coverage metrics Pydantic schemas."""
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class OverviewReportResponse(BaseModel):
    total_products: int
    complete_products: int
    incomplete_products: int
    total_categories: int
    total_manufacturers: int
    active_jobs: int
    completed_jobs: int
    total_urls_processed: int
    total_urls_failed: int
    total_urls_inaccessible: int


class CoverageReportResponse(BaseModel):
    discovered_urls: int
    queued_urls: int
    in_progress_urls: int
    processed_urls: int
    failed_retryable_urls: int
    failed_terminal_urls: int
    inaccessible_urls: int
    skipped_urls: int
    unique_products_extracted: int
    products_with_sku: int
    products_with_ean: int
    products_with_price: int
    products_with_specs: int
    overall_crawl_completion_rate: float = Field(..., description="processed / (discovered - skipped)")


class CompletenessReportResponse(BaseModel):
    total_products: int
    sku_fill_rate: float
    ean_fill_rate: float
    price_fill_rate: float
    description_fill_rate: float
    images_fill_rate: float
    specifications_fill_rate: float


class ErrorReportResponse(BaseModel):
    total_errors: int
    retryable_errors: int
    terminal_errors: int
    inaccessible_access_restricted: int
    by_error_type: Dict[str, int]
