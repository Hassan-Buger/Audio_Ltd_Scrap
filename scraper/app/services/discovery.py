"""Seed discovery service."""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.repositories.url_repo import URLRepository
from app.schemas.crawl import URLType

DEFAULT_SEEDS = [
    "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1",
    "https://www.audiovideo.lt/gamintojai/hertz",
    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison",
    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit"
]


def init_job_seeds(db: Session, job_id: int, custom_seeds: Optional[List[str]] = None) -> int:
    """Initialize seed URLs for a crawl job."""
    seeds = custom_seeds if custom_seeds else DEFAULT_SEEDS
    return URLRepository.enqueue_batch(db, job_id, seeds, depth=0)
