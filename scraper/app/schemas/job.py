"""Job lifecycle and control Pydantic schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class JobScope(str, Enum):
    FULL = "full"
    CATEGORY = "category"
    MANUFACTURER = "manufacturer"
    SEARCH = "search"
    CUSTOM_URLS = "custom_urls"


class CrawlJobCreate(BaseModel):
    scope: JobScope = Field(default=JobScope.FULL, description="Scope of the crawl")
    seed_urls: Optional[List[str]] = Field(default=None, description="Optional custom seed URLs")
    category_id: Optional[int] = Field(default=None, description="Target category ID if scope is category")
    manufacturer_id: Optional[int] = Field(default=None, description="Target manufacturer ID if scope is manufacturer")
    search_query: Optional[str] = Field(default=None, description="Search keyword if scope is search")
    max_depth: Optional[int] = Field(default=10, ge=1, le=50)
    max_urls: Optional[int] = Field(default=10000, ge=1, le=100000)
    use_playwright: bool = Field(default=False, description="Enable Playwright browser fallback")


class CrawlJobProgressResponse(BaseModel):
    job_id: int
    status: JobStatus
    urls_discovered: int
    urls_queued: int
    urls_in_progress: int
    urls_processed: int
    urls_failed_retryable: int
    urls_failed_terminal: int
    urls_inaccessible: int
    products_extracted: int
    products_incomplete: int
    percentage_completed: float


class CrawlJobResponse(BaseModel):
    id: int
    scope: JobScope
    status: JobStatus
    config: Dict[str, Any]
    urls_discovered: int
    urls_processed: int
    products_extracted: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CrawlJobErrorItem(BaseModel):
    id: int
    url: str
    error_type: str
    error_message: str
    is_retryable: bool
    created_at: datetime
