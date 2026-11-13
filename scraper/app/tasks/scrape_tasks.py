"""Celery asynchronous scraping tasks."""
import logging
from app.tasks.celery_app import celery_app
from app.database.session import transaction_scope
from app.services.job_runner import JobRunner
from app.database.repositories.job_repo import JobRepository
from app.schemas.job import JobStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_scrape_batch", bind=True, max_retries=3)
def run_scrape_batch(self, job_id: int, batch_size: int = 10):
    """Celery background task for running crawl batches."""
    try:
        with transaction_scope() as db:
            job = JobRepository.get_job(db, job_id)
            if not job or job.status in (JobStatus.PAUSED.value, JobStatus.CANCELLED.value, JobStatus.COMPLETED.value):
                return {"status": "skipped", "job_id": job_id}

            processed = JobRunner.run_job_batch(db, job_id, worker_id=self.request.id, batch_size=batch_size)
            
            # If items were processed and job is still active, dispatch next batch
            progress = JobRepository.get_progress(db, job_id)
            if progress and progress.status == JobStatus.RUNNING and progress.urls_queued > 0:
                run_scrape_batch.delay(job_id=job_id, batch_size=batch_size)

            return {
                "status": "batch_completed",
                "job_id": job_id,
                "urls_processed": processed
            }
    except Exception as e:
        logger.error(f"Error processing scrape batch for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=10)
