"""Tests for durable URL frontier and lease mechanics."""
from datetime import datetime, timezone, timedelta
from app.database.repositories.job_repo import JobRepository
from app.database.repositories.url_repo import URLRepository
from app.schemas.job import JobScope
from app.schemas.crawl import URLStatus


def test_frontier_idempotency_and_leases(db):
    job = JobRepository.create_job(db, scope=JobScope.FULL)
    db.commit()

    test_url = "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1"
    
    # 1. Enqueue
    u1 = URLRepository.enqueue_url(db, job.id, test_url)
    db.commit()
    assert u1 is not None
    assert u1.status == URLStatus.QUEUED.value

    # 2. Duplicate enqueue must return existing URL without creating duplicate
    u2 = URLRepository.enqueue_url(db, job.id, test_url)
    db.commit()
    assert u2.id == u1.id

    # 3. Worker claims URL with lease
    claimed = URLRepository.claim_urls(db, job.id, worker_id="worker-test-1", batch_size=10, lease_seconds=60)
    db.commit()
    assert len(claimed) == 1
    assert claimed[0].status == URLStatus.IN_PROGRESS.value
    assert claimed[0].lease_id == "worker-test-1"

    # 4. Another worker cannot claim the same in-progress URL
    claimed2 = URLRepository.claim_urls(db, job.id, worker_id="worker-test-2", batch_size=10)
    db.commit()
    assert len(claimed2) == 0

    # 5. Simulate expired lease and verify recovery
    claimed[0].lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db.commit()

    reclaimed_count = URLRepository.reclaim_expired_leases(db, job.id)
    db.commit()
    assert reclaimed_count == 1
    assert claimed[0].status == URLStatus.QUEUED.value

    # 6. Mark processed
    URLRepository.mark_processed(db, claimed[0].id, http_status=200)
    db.commit()
    assert claimed[0].status == URLStatus.PROCESSED.value
