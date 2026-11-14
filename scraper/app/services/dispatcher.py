"""Job dispatch service with automatic local background worker fallback."""
import logging
import threading
from typing import Optional
from fastapi import BackgroundTasks
from app.config import settings
from app.database.session import transaction_scope
from app.services.job_runner import JobRunner

logger = logging.getLogger(__name__)


class JobDispatcher:
    @classmethod
    def run_job_sync(cls, job_id: int, batch_size: int = 10, max_batches: int = 500) -> int:
        """Process batches synchronously until queue is empty or job finished."""
        total_processed = 0
        batches = 0
        logger.info(f"Starting execution loop for job #{job_id}")

        while batches < max_batches:
            with transaction_scope() as db:
                processed = JobRunner.run_job_batch(db, job_id=job_id, batch_size=batch_size)
                total_processed += processed
                batches += 1
                if processed == 0:
                    break

        logger.info(
            f"Finished execution loop for job #{job_id}: {total_processed} URLs processed across {batches} batches"
        )
        return total_processed

    @classmethod
    def dispatch_job(cls, job_id: int, background_tasks: Optional[BackgroundTasks] = None) -> str:
        """
        Dispatches a job.
        1. Attempts Celery dispatch if broker is configured and reachable.
        2. Falls back to FastAPI BackgroundTasks or daemon thread so jobs run automatically in development.
        """
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
            r.ping()
            from app.tasks.scrape_tasks import run_scrape_batch
            run_scrape_batch.delay(job_id=job_id)
            logger.info(f"Job #{job_id} dispatched to Celery worker")
            return "celery"
        except Exception as e:
            logger.info(f"Celery broker unavailable ({e}); falling back to local background execution")

        if background_tasks:
            background_tasks.add_task(cls.run_job_sync, job_id)
            return "background_task"
        else:
            thread = threading.Thread(target=cls.run_job_sync, args=(job_id,), daemon=True)
            thread.start()
            return "thread"
