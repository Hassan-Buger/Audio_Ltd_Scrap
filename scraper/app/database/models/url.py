"""Durable URL Frontier and Product Source Provenance models."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from .base import Base


class ProductSource(Base):
    __tablename__ = "product_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url = Column(String(2048), nullable=False, index=True)
    discovery_type = Column(String(50), nullable=False)  # category, manufacturer, search, direct
    crawl_job_id = Column(Integer, ForeignKey("crawl_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="sources")


class CrawlURL(Base):
    __tablename__ = "crawl_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crawl_job_id = Column(Integer, ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    normalized_url = Column(String(2048), nullable=False, index=True)
    url_type = Column(String(50), nullable=False, default="unknown", index=True)  # category, manufacturer, search, pagination, product
    status = Column(String(50), nullable=False, default="discovered", index=True)  # discovered, queued, in_progress, processed, failed_retryable, failed_terminal, skipped, inaccessible
    depth = Column(Integer, default=0, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    
    # Distributed lease for worker claims
    lease_id = Column(String(255), nullable=True, index=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    http_status = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("CrawlJob", back_populates="urls")

    __table_args__ = (
        Index("idx_crawl_urls_job_status", "crawl_job_id", "status"),
        Index("idx_crawl_urls_lease", "status", "lease_expires_at"),
        Index("idx_crawl_urls_job_normalized", "crawl_job_id", "normalized_url", unique=True),
    )
