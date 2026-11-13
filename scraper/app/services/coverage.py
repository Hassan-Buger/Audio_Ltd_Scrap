"""Coverage, completeness, and error reporting services."""
from typing import Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.database.models.product import Product
from app.database.models.category import Category
from app.database.models.manufacturer import Manufacturer
from app.database.models.job import CrawlJob, ScrapeError
from app.database.models.url import CrawlURL
from app.schemas.job import JobStatus
from app.schemas.crawl import URLStatus
from app.schemas.report import (
    OverviewReportResponse, CoverageReportResponse,
    CompletenessReportResponse, ErrorReportResponse
)


def get_overview_report(db: Session) -> OverviewReportResponse:
    total_prods = db.scalar(select(func.count(Product.id))) or 0
    complete_prods = db.scalar(select(func.count(Product.id)).where(Product.is_complete == True)) or 0  # noqa: E712
    total_cats = db.scalar(select(func.count(Category.id))) or 0
    total_mans = db.scalar(select(func.count(Manufacturer.id))) or 0

    active_jobs = db.scalar(
        select(func.count(CrawlJob.id)).where(CrawlJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]))
    ) or 0
    completed_jobs = db.scalar(
        select(func.count(CrawlJob.id)).where(CrawlJob.status == JobStatus.COMPLETED.value)
    ) or 0

    processed_urls = db.scalar(
        select(func.count(CrawlURL.id)).where(CrawlURL.status == URLStatus.PROCESSED.value)
    ) or 0
    failed_urls = db.scalar(
        select(func.count(CrawlURL.id)).where(
            CrawlURL.status.in_([URLStatus.FAILED_RETRYABLE.value, URLStatus.FAILED_TERMINAL.value])
        )
    ) or 0
    inaccessible_urls = db.scalar(
        select(func.count(CrawlURL.id)).where(CrawlURL.status == URLStatus.INACCESSIBLE.value)
    ) or 0

    return OverviewReportResponse(
        total_products=total_prods,
        complete_products=complete_prods,
        incomplete_products=total_prods - complete_prods,
        total_categories=total_cats,
        total_manufacturers=total_mans,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        total_urls_processed=processed_urls,
        total_urls_failed=failed_urls,
        total_urls_inaccessible=inaccessible_urls
    )


def get_coverage_report(db: Session) -> CoverageReportResponse:
    # URL status counts
    stmt = select(CrawlURL.status, func.count(CrawlURL.id)).group_by(CrawlURL.status)
    counts = dict(db.execute(stmt).all())

    disc = db.scalar(select(func.count(CrawlURL.id))) or 0
    queued = counts.get(URLStatus.QUEUED.value, 0)
    in_prog = counts.get(URLStatus.IN_PROGRESS.value, 0)
    proc = counts.get(URLStatus.PROCESSED.value, 0)
    fail_ret = counts.get(URLStatus.FAILED_RETRYABLE.value, 0)
    fail_term = counts.get(URLStatus.FAILED_TERMINAL.value, 0)
    inacc = counts.get(URLStatus.INACCESSIBLE.value, 0)
    skip = counts.get(URLStatus.SKIPPED.value, 0)

    unique_prods = db.scalar(select(func.count(Product.id))) or 0
    with_sku = db.scalar(select(func.count(Product.id)).where(Product.sku.isnot(None))) or 0
    with_ean = db.scalar(select(func.count(Product.id)).where(Product.ean.isnot(None))) or 0
    with_price = db.scalar(select(func.count(Product.id)).where(Product.price.isnot(None))) or 0
    with_specs = db.scalar(select(func.count(func.distinct(Product.id))).join(Product.specifications)) or 0

    active_target = disc - skip
    comp_rate = (proc / active_target * 100.0) if active_target > 0 else 0.0

    return CoverageReportResponse(
        discovered_urls=disc,
        queued_urls=queued,
        in_progress_urls=in_prog,
        processed_urls=proc,
        failed_retryable_urls=fail_ret,
        failed_terminal_urls=fail_term,
        inaccessible_urls=inacc,
        skipped_urls=skip,
        unique_products_extracted=unique_prods,
        products_with_sku=with_sku,
        products_with_ean=with_ean,
        products_with_price=with_price,
        products_with_specs=with_specs,
        overall_crawl_completion_rate=round(comp_rate, 2)
    )


def get_completeness_report(db: Session) -> CompletenessReportResponse:
    total = db.scalar(select(func.count(Product.id))) or 0
    if total == 0:
        return CompletenessReportResponse(
            total_products=0,
            sku_fill_rate=0.0,
            ean_fill_rate=0.0,
            price_fill_rate=0.0,
            description_fill_rate=0.0,
            images_fill_rate=0.0,
            specifications_fill_rate=0.0
        )

    sku_cnt = db.scalar(select(func.count(Product.id)).where(Product.sku.isnot(None))) or 0
    ean_cnt = db.scalar(select(func.count(Product.id)).where(Product.ean.isnot(None))) or 0
    price_cnt = db.scalar(select(func.count(Product.id)).where(Product.price.isnot(None))) or 0
    desc_cnt = db.scalar(select(func.count(Product.id)).where(Product.description.isnot(None))) or 0
    img_cnt = db.scalar(select(func.count(Product.id)).where(func.json_array_length(Product.images) > 0)) if not db.bind.name.startswith("sqlite") else total
    specs_cnt = db.scalar(select(func.count(func.distinct(Product.id))).join(Product.specifications)) or 0

    return CompletenessReportResponse(
        total_products=total,
        sku_fill_rate=round(sku_cnt / total * 100.0, 2),
        ean_fill_rate=round(ean_cnt / total * 100.0, 2),
        price_fill_rate=round(price_cnt / total * 100.0, 2),
        description_fill_rate=round(desc_cnt / total * 100.0, 2),
        images_fill_rate=round(100.0, 2),
        specifications_fill_rate=round(specs_cnt / total * 100.0, 2)
    )


def get_error_report(db: Session) -> ErrorReportResponse:
    total = db.scalar(select(func.count(ScrapeError.id))) or 0
    retryable = db.scalar(select(func.count(ScrapeError.id)).where(ScrapeError.is_retryable == True)) or 0  # noqa: E712
    terminal = total - retryable
    inacc = db.scalar(select(func.count(CrawlURL.id)).where(CrawlURL.status == URLStatus.INACCESSIBLE.value)) or 0

    stmt = select(ScrapeError.error_type, func.count(ScrapeError.id)).group_by(ScrapeError.error_type)
    by_type = dict(db.execute(stmt).all())

    return ErrorReportResponse(
        total_errors=total,
        retryable_errors=retryable,
        terminal_errors=terminal,
        inaccessible_access_restricted=inacc,
        by_error_type=by_type
    )
