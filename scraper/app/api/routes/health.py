"""Health and system status routes."""
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.dependencies import get_db
from app.schemas.common import APIResponse
from app.services.coverage import get_overview_report

router = APIRouter(tags=["Health & System"])


@router.get("/health", response_model=APIResponse[dict])
def health_check():
    """Basic application liveness check."""
    return APIResponse(
        success=True,
        message="Application is healthy",
        data={"status": "ok"}
    )


@router.get("/health/ready", response_model=APIResponse[dict])
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """Readiness check including database connectivity."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return APIResponse(
            success=False,
            message="Database unavailable",
            data={"database": "down", "error": str(e)}
        )

    return APIResponse(
        success=True,
        message="All dependencies ready",
        data={"database": "up"}
    )


@router.get("/system/status", response_model=APIResponse[dict])
def system_status(db: Session = Depends(get_db)):
    """Overall scraper system status."""
    overview = get_overview_report(db)
    return APIResponse(
        success=True,
        message="System status retrieved",
        data={
            "status": "operational",
            "active_jobs": overview.active_jobs,
            "total_products": overview.total_products,
            "urls_processed": overview.total_urls_processed,
            "urls_inaccessible": overview.total_urls_inaccessible
        }
    )


@router.get("/system/stats", response_model=APIResponse[dict])
def system_stats(db: Session = Depends(get_db)):
    """Product, category, job and crawl statistics."""
    overview = get_overview_report(db)
    return APIResponse(
        success=True,
        message="System statistics retrieved",
        data=overview.model_dump()
    )
