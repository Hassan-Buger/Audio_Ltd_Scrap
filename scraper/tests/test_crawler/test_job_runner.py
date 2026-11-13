"""Tests for JobRunner batch execution and Cloudflare/403 access restriction handling."""
from unittest.mock import patch, MagicMock
from app.services.job_runner import JobRunner
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.schemas.job import JobScope, JobStatus
from app.schemas.crawl import URLStatus, URLType


def test_job_runner_handles_cloudflare_challenge_as_inaccessible(db):
    job = JobRepository.create_job(db, scope=JobScope.FULL)
    u = URLRepository.enqueue_url(db, job.id, "https://www.audiovideo.lt/gamintojai/hertz")
    db.commit()

    # Simulate 403 Forbidden Cloudflare response
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "<!DOCTYPE html><html><title>Just a moment...</title>challenges.cloudflare.com</html>"
    mock_resp.headers = {"Cf-Mitigated": "challenge"}

    with patch("httpx.Client.get", return_value=mock_resp):
        res = JobRunner.process_url(db, job.id, u)
        db.commit()

    assert res["status"] == "inaccessible"
    assert u.status == URLStatus.INACCESSIBLE.value
    assert "Cloudflare" in u.last_error

    # Verify error is durably recorded in scrape_errors
    errors = JobRepository.get_job_errors(db, job.id)
    assert len(errors) == 1
    assert errors[0].error_type == "ACCESS_RESTRICTED"


def test_job_runner_extracts_and_persists_product_on_200(db, sample_product_html):
    job = JobRepository.create_job(db, scope=JobScope.FULL)
    u = URLRepository.enqueue_url(
        db, job.id, "https://www.audiovideo.lt/hertz-ml-700-set-midrange",
        forced_type=URLType.PRODUCT
    )
    db.commit()

    # Simulate 200 OK product detail page
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_product_html
    mock_resp.url = "https://www.audiovideo.lt/hertz-ml-700-set-midrange"
    mock_resp.headers = {"Content-Type": "text/html; charset=UTF-8"}

    with patch("httpx.Client.get", return_value=mock_resp):
        res = JobRunner.process_url(db, job.id, u)
        db.commit()

    assert res["status"] == "processed"
    assert u.status == URLStatus.PROCESSED.value

    # Verify product in repository
    from app.database.repositories.product_repo import ProductRepository
    prod = ProductRepository.get_by_sku(db, "ML-700-3")
    assert prod is not None
    assert prod.title == "Hertz ML 700.3 Legend"
    assert prod.price == 349.0
    assert len(prod.specifications) == 3
