"""Category repository for CRUD and hierarchical category operations."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.database.models.category import Category, ProductCategory
from app.schemas.category import CategoryCreate, CategoryTreeNode, CategoryCoverageResponse


class CategoryRepository:
    @staticmethod
    def upsert_category(db: Session, data: CategoryCreate) -> Category:
        """Create or update a category record idempotently by source_url or slug."""
        stmt = select(Category).where(
            (Category.source_url == data.source_url) | (Category.slug == data.slug)
        )
        cat = db.execute(stmt).scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if cat:
            cat.name = data.name
            cat.level = data.level
            cat.is_leaf = data.is_leaf
            if data.parent_id is not None:
                cat.parent_id = data.parent_id
            if data.product_count_source is not None:
                cat.product_count_source = data.product_count_source
            cat.updated_at = now
        else:
            cat = Category(
                name=data.name,
                slug=data.slug,
                source_url=data.source_url,
                parent_id=data.parent_id,
                level=data.level,
                is_leaf=data.is_leaf,
                product_count_observed=0,
                product_count_source=data.product_count_source,
                created_at=now,
                updated_at=now
            )
            db.add(cat)

        db.flush()
        return cat

    @staticmethod
    def get_by_id(db: Session, category_id: int) -> Optional[Category]:
        return db.get(Category, category_id)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Category]:
        stmt = select(Category).where(Category.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_categories(
        db: Session,
        parent_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Category]:
        stmt = select(Category)
        if parent_id is not None:
            stmt = stmt.where(Category.parent_id == parent_id)
        stmt = stmt.order_by(Category.level.asc(), Category.name.asc()).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_children(db: Session, category_id: int) -> List[Category]:
        stmt = select(Category).where(Category.parent_id == category_id).order_by(Category.name.asc())
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_tree(db: Session) -> List[CategoryTreeNode]:
        """Construct the complete hierarchical tree of categories."""
        stmt = (
            select(Category)
            .where(Category.parent_id.is_(None))
            .order_by(Category.name.asc())
        )
        roots = list(db.execute(stmt).scalars().all())
        return [CategoryTreeNode.model_validate(r) for r in roots]

    @staticmethod
    def get_coverage(db: Session) -> CategoryCoverageResponse:
        total = db.scalar(select(func.count(Category.id))) or 0
        roots = db.scalar(select(func.count(Category.id)).where(Category.parent_id.is_(None))) or 0
        subs = total - roots
        leaves = db.scalar(select(func.count(Category.id)).where(Category.is_leaf == True)) or 0  # noqa: E712
        with_prods = db.scalar(select(func.count(Category.id)).where(Category.product_count_observed > 0)) or 0
        
        cov = (with_prods / total * 100.0) if total > 0 else 0.0

        return CategoryCoverageResponse(
            total_categories_discovered=total,
            root_categories=roots,
            subcategories=subs,
            leaf_categories=leaves,
            categories_with_products=with_prods,
            coverage_percentage=round(cov, 2)
        )
