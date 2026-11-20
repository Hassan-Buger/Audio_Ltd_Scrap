"""Export Pydantic schemas."""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"


class ExportType(str, Enum):
    PRODUCTS = "products"
    CATEGORIES = "categories"
    JOB_RESULTS = "job_results"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportCreateRequest(BaseModel):
    export_type: ExportType
    format: ExportFormat
    category_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    job_id: Optional[int] = None
    language: str = "lt"

    model_config = {"json_schema_extra": {
        "example": {
            "export_type": "products",
            "format": "csv",
            "language": "lt",
        },
        "examples": [
            {
                "export_type": "products",
                "format": "csv",
                "language": "lt",
            }
        ]
    }}


class ExportStatusResponse(BaseModel):
    export_id: str
    export_type: ExportType
    format: ExportFormat
    status: ExportStatus
    file_path: Optional[str] = None
    total_records: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
