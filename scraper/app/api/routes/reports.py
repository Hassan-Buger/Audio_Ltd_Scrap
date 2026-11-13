"""Reports and analytics API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.schemas.common import APIResponse
from app.schemas.report import (
    OverviewReportResponse, CoverageReportResponse,
    CompletenessReportResponse, ErrorReportResponse
)
from app.schemas.category import CategoryCoverageResponse
from app.schemas.manufacturer import ManufacturerCoverageResponse
from app.services.coverage import (
    get_overview_report, get_coverage_report,
    get_completeness_report, get_error_report
)
from app.database.repositories.category_repo import CategoryRepository
from app.database.repositories.manufacturer_repo import ManufacturerRepository

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/overview", response_model=APIResponse[OverviewReportResponse])
def overview_report(db: Session = Depends(get_db)):
    """Overall scraping catalogue overview."""
    rep = get_overview_report(db)
    return APIResponse(success=True, message="Overview report generated", data=rep)


@router.get("/coverage", response_model=APIResponse[CoverageReportResponse])
def coverage_report(db: Session = Depends(get_db)):
    """Category and product coverage report with explicit denominators."""
    rep = get_coverage_report(db)
    return APIResponse(success=True, message="Coverage report generated", data=rep)


@router.get("/completeness", response_model=APIResponse[CompletenessReportResponse])
def completeness_report(db: Session = Depends(get_db)):
    """Data completeness statistics across product fields."""
    rep = get_completeness_report(db)
    return APIResponse(success=True, message="Completeness report generated", data=rep)


@router.get("/errors", response_model=APIResponse[ErrorReportResponse])
def error_report(db: Session = Depends(get_db)):
    """Scraping failure and access-restriction summary."""
    rep = get_error_report(db)
    return APIResponse(success=True, message="Error report generated", data=rep)


@router.get("/manufacturers", response_model=APIResponse[ManufacturerCoverageResponse])
def manufacturer_report(db: Session = Depends(get_db)):
    """Manufacturer-level coverage report."""
    rep = ManufacturerRepository.get_coverage(db)
    return APIResponse(success=True, message="Manufacturer coverage generated", data=rep)


@router.get("/categories", response_model=APIResponse[CategoryCoverageResponse])
def category_report(db: Session = Depends(get_db)):
    """Category-level extraction report."""
    rep = CategoryRepository.get_coverage(db)
    return APIResponse(success=True, message="Category coverage generated", data=rep)
