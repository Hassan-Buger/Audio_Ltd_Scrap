"""Common response envelopes, pagination schemas, and error structures."""
from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=50, ge=1, le=500, description="Items per page")
    total: int = Field(default=0, ge=0, description="Total matching items")
    total_pages: int = Field(default=0, ge=0, description="Total number of pages")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None
    meta: Optional[PaginationMeta] = None


class ErrorDetail(BaseModel):
    code: str
    details: Optional[Dict[str, Any]] = None


class APIErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: ErrorDetail
