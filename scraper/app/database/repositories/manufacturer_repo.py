"""Manufacturer repository."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database.models.manufacturer import Manufacturer
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerCoverageResponse


class ManufacturerRepository:
    @staticmethod
    def upsert_manufacturer(db: Session, data: ManufacturerCreate) -> Manufacturer:
        stmt = select(Manufacturer).where(
            (Manufacturer.slug == data.slug) | (Manufacturer.name == data.name)
        )
        man = db.execute(stmt).scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if man:
            man.name = data.name
            if data.source_url:
                man.source_url = data.source_url
            if data.product_count_source is not None:
                man.product_count_source = data.product_count_source
            man.updated_at = now
        else:
            man = Manufacturer(
                name=data.name,
                slug=data.slug,
                source_url=data.source_url,
                product_count_observed=0,
                product_count_source=data.product_count_source,
                created_at=now,
                updated_at=now
            )
            db.add(man)

        db.flush()
        return man

    @staticmethod
    def get_by_id(db: Session, man_id: int) -> Optional[Manufacturer]:
        return db.get(Manufacturer, man_id)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Manufacturer]:
        stmt = select(Manufacturer).where(Manufacturer.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_manufacturers(db: Session, skip: int = 0, limit: int = 100) -> List[Manufacturer]:
        stmt = select(Manufacturer).order_by(Manufacturer.name.asc()).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_coverage(db: Session) -> ManufacturerCoverageResponse:
        total = db.scalar(select(func.count(Manufacturer.id))) or 0
        with_prods = db.scalar(select(func.count(Manufacturer.id)).where(Manufacturer.product_count_observed > 0)) or 0
        cov = (with_prods / total * 100.0) if total > 0 else 0.0

        return ManufacturerCoverageResponse(
            total_manufacturers=total,
            manufacturers_with_products=with_prods,
            coverage_percentage=round(cov, 2)
        )
