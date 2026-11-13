"""Data export API endpoints."""
import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.export import ExportCreateRequest, ExportStatusResponse, ExportStatus, ExportType, ExportFormat
from app.services.export import ExportService

router = APIRouter(prefix="/exports", tags=["Exports"])

# In-memory export status registry for custom asynchronous exports
EXPORT_JOBS = {}


@router.get("/products/csv")
def export_products_csv(
    category_id: Optional[int] = None,
    manufacturer_id: Optional[int] = None,
    job_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Export products as streaming CSV."""
    stream = ExportService.export_products_csv(
        db, category_id=category_id, manufacturer_id=manufacturer_id, job_id=job_id
    )
    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"}
    )


@router.get("/products/json")
def export_products_json(
    category_id: Optional[int] = None,
    manufacturer_id: Optional[int] = None,
    job_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Export products as streaming JSON."""
    stream = ExportService.export_products_json(
        db, category_id=category_id, manufacturer_id=manufacturer_id, job_id=job_id
    )
    return StreamingResponse(
        stream,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=products.json"}
    )


@router.get("/categories/json")
def export_categories_json(db: Session = Depends(get_db)):
    """Export full category tree as JSON."""
    data = ExportService.export_categories_json(db)
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=categories.json"}
    )


@router.get("/jobs/{job_id}")
def export_job_results(job_id: int, format: str = Query("json", pattern="^(csv|json)$"), db: Session = Depends(get_db)):
    """Export results from a specific scrape job."""
    if format == "csv":
        stream = ExportService.export_products_csv(db, job_id=job_id)
        return StreamingResponse(
            stream, media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=job_{job_id}_products.csv"}
        )
    stream = ExportService.export_products_json(db, job_id=job_id)
    return StreamingResponse(
        stream, media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=job_{job_id}_products.json"}
    )


@router.post("/create", response_model=APIResponse[ExportStatusResponse])
def create_custom_export(
    payload: ExportCreateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Create a tracked custom export request."""
    export_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    rec = ExportStatusResponse(
        export_id=export_id,
        export_type=payload.export_type,
        format=payload.format,
        status=ExportStatus.COMPLETED,
        file_path=f"/api/v1/exports/{export_id}/download",
        total_records=0,
        created_at=now,
        completed_at=now
    )
    EXPORT_JOBS[export_id] = rec
    return APIResponse(success=True, message="Export task created", data=rec)


@router.get("/{export_id}/status", response_model=APIResponse[ExportStatusResponse])
def get_export_status(export_id: str):
    """Check export generation status."""
    if export_id not in EXPORT_JOBS:
        raise HTTPException(status_code=404, detail="Export ID not found")
    return APIResponse(success=True, message="Export status retrieved", data=EXPORT_JOBS[export_id])


@router.get("/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db)):
    """Download generated export."""
    if export_id not in EXPORT_JOBS:
        raise HTTPException(status_code=404, detail="Export ID not found")
    job = EXPORT_JOBS[export_id]
    if job.format == ExportFormat.CSV:
        return export_products_csv(db=db)
    return export_products_json(db=db)
