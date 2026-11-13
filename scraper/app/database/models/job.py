"""Crawl job and execution tracking models."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.orm import relationship
from .base import Base


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(50), nullable=False, default="full", index=True)
    status = Column(String(50), nullable=False, default="queued", index=True)
    config = Column(JSON, default=dict, nullable=False)
    urls_discovered = Column(Integer, default=0, nullable=False)
    urls_processed = Column(Integer, default=0, nullable=False)
    products_extracted = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    urls = relationship("CrawlURL", back_populates="job", cascade="all, delete-orphan")
    runs = relationship("ScrapeRun", back_populates="job", cascade="all, delete-orphan")
    errors = relationship("ScrapeError", back_populates="job", cascade="all, delete-orphan")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    urls_processed = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="running", nullable=False)

    job = relationship("CrawlJob", back_populates="runs")


class ScrapeError(Base):
    __tablename__ = "scrape_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("crawl_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    url = Column(String(2048), nullable=False, index=True)
    stage = Column(String(50), nullable=False, index=True)  # fetch, parse, persist
    error_type = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    is_retryable = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("CrawlJob", back_populates="errors")
