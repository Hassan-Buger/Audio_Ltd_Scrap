"""URL Frontier and crawl tracking Pydantic schemas."""
from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class URLStatus(str, Enum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    PROCESSED = "processed"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    SKIPPED = "skipped"
    INACCESSIBLE = "inaccessible"


class URLType(str, Enum):
    CATEGORY = "category"
    MANUFACTURER = "manufacturer"
    SEARCH = "search"
    PAGINATION = "pagination"
    PRODUCT = "product"
    UNKNOWN = "unknown"


class CrawlURLResponse(BaseModel):
    id: int
    crawl_job_id: int
    url: str
    normalized_url: str
    url_type: URLType
    status: URLStatus
    depth: int
    attempts: int
    last_error: Optional[str] = None
    http_status: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlFailedURLResponse(BaseModel):
    id: int
    crawl_job_id: int
    url: str
    url_type: URLType
    status: URLStatus
    attempts: int
    last_error: Optional[str] = None
    http_status: Optional[int] = None
    is_retryable: bool
    updated_at: datetime
