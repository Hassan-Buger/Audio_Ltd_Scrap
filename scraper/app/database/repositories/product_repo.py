"""Product repository with conservative deduplication and provenance tracking."""
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
from sqlalchemy import select, update, func, or_, and_, desc, asc
from sqlalchemy.orm import Session, joinedload
from app.database.models.product import Product, ProductSpecification, PriceHistory
from app.database.models.category import Category, ProductCategory
from app.database.models.manufacturer import Manufacturer
from app.database.models.url import ProductSource
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    @staticmethod
    def find_existing_product(
        db: Session,
        canonical_url: str,
        sku: Optional[str] = None,
        ean: Optional[str] = None,
        brand_name: Optional[str] = None
    ) -> Optional[Product]:
        """
        Conservative product identity resolution:
        1. EAN/GTIN if present (strong global identifier)
        2. SKU + Brand if present (strong retailer/brand identifier)
        3. Canonical URL match
        Variants are not merged based solely on similar titles.
        """
        # 1. EAN check
        if ean:
            prod = db.execute(select(Product).where(Product.ean == ean)).scalar_one_or_none()
            if prod:
                return prod

        # 2. SKU + Brand check
        if sku and brand_name:
            prod = db.execute(
                select(Product).where(
                    and_(Product.sku == sku, func.lower(Product.brand_name) == func.lower(brand_name))
                )
            ).scalar_one_or_none()
            if prod:
                return prod

        # 3. Canonical URL match
        if canonical_url:
            prod = db.execute(
                select(Product).where(Product.canonical_url == canonical_url)
            ).scalar_one_or_none()
            if prod:
                return prod

        return None

    @staticmethod
    def upsert_product(db: Session, data: ProductCreate) -> Tuple[Product, bool]:
        """
        Create or update a product record, managing relationships, specs, price history, and provenance.
        Returns: (product, is_new)
        """
        now = datetime.now(timezone.utc)
        existing = ProductRepository.find_existing_product(
            db,
            canonical_url=data.canonical_url,
            sku=data.sku,
            ean=data.ean,
            brand_name=data.brand_name
        )

        is_new = False
        if existing:
            prod = existing
            # Update mutable fields without overwriting non-null values with null
            if data.title and not prod.title:
                prod.title = data.title
            if data.sku and not prod.sku:
                prod.sku = data.sku
            if data.ean and not prod.ean:
                prod.ean = data.ean
            if data.model and not prod.model:
                prod.model = data.model
            if data.brand_name and not prod.brand_name:
                prod.brand_name = data.brand_name
            if data.description and not prod.description:
                prod.description = data.description
            if data.images and not prod.images:
                prod.images = data.images

            # Check price change for history
            if data.price is not None and prod.price != data.price:
                history = PriceHistory(
                    product_id=prod.id,
                    price=data.price,
                    regular_price=data.regular_price,
                    currency=data.currency,
                    observed_at=now
                )
                db.add(history)
                prod.price = data.price
                prod.regular_price = data.regular_price

            if data.availability is not None:
                prod.availability = data.availability
            if data.in_stock is not None:
                prod.in_stock = data.in_stock

            prod.is_complete = data.is_complete
            prod.updated_at = now
        else:
            is_new = True
            prod = Product(
                canonical_url=data.canonical_url,
                title=data.title,
                sku=data.sku,
                ean=data.ean,
                model=data.model,
                manufacturer_id=data.manufacturer_id,
                brand_name=data.brand_name,
                price=data.price,
                regular_price=data.regular_price,
                currency=data.currency,
                availability=data.availability,
                in_stock=data.in_stock,
                description=data.description,
                images=data.images,
                is_complete=data.is_complete,
                created_at=now,
                updated_at=now
            )
            db.add(prod)
            db.flush()

            # Record initial price in history if price exists
            if data.price is not None:
                history = PriceHistory(
                    product_id=prod.id,
                    price=data.price,
                    regular_price=data.regular_price,
                    currency=data.currency,
                    observed_at=now
                )
                db.add(history)

        # Handle Brand/Manufacturer link if manufacturer_id not already set
        if not prod.manufacturer_id and prod.brand_name:
            man = db.execute(
                select(Manufacturer).where(func.lower(Manufacturer.name) == func.lower(prod.brand_name))
            ).scalar_one_or_none()
            if man:
                prod.manufacturer_id = man.id
                man.product_count_observed += 1

        # Add ProductSource provenance
        source_url = data.source_url or data.canonical_url
        existing_src = db.execute(
            select(ProductSource).where(
                and_(ProductSource.product_id == prod.id, ProductSource.source_url == source_url)
            )
        ).scalar_one_or_none()
        if not existing_src:
            db.add(ProductSource(
                product_id=prod.id,
                source_url=source_url,
                discovery_type=data.discovery_type,
                crawl_job_id=data.crawl_job_id,
                discovered_at=now
            ))

        # Add category relationships
        for cat_id in data.category_ids:
            rel = db.execute(
                select(ProductCategory).where(
                    and_(ProductCategory.product_id == prod.id, ProductCategory.category_id == cat_id)
                )
            ).scalar_one_or_none()
            if not rel:
                db.add(ProductCategory(
                    product_id=prod.id,
                    category_id=cat_id,
                    crawl_job_id=data.crawl_job_id,
                    discovered_at=now
                ))
                cat = db.get(Category, cat_id)
                if cat:
                    cat.product_count_observed += 1

        # Add/update specifications
        existing_specs = {s.label.lower(): s for s in prod.specifications}
        for item in data.specifications:
            lbl_lower = item.label.lower()
            if lbl_lower not in existing_specs:
                spec = ProductSpecification(
                    product_id=prod.id,
                    label=item.label,
                    value=item.value,
                    numeric_value=item.numeric_value,
                    unit=item.unit
                )
                db.add(spec)
                existing_specs[lbl_lower] = spec

        db.flush()
        return prod, is_new

    @staticmethod
    def get_by_id(db: Session, product_id: int) -> Optional[Product]:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                joinedload(Product.specifications),
                joinedload(Product.sources),
                joinedload(Product.translations),
                joinedload(Product.categories)
            )
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    @staticmethod
    def get_by_sku(db: Session, sku: str) -> Optional[Product]:
        stmt = (
            select(Product)
            .where(Product.sku == sku)
            .options(
                joinedload(Product.specifications),
                joinedload(Product.sources),
                joinedload(Product.translations)
            )
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    @staticmethod
    def get_by_ean(db: Session, ean: str) -> Optional[Product]:
        stmt = (
            select(Product)
            .where(Product.ean == ean)
            .options(
                joinedload(Product.specifications),
                joinedload(Product.sources),
                joinedload(Product.translations)
            )
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    @staticmethod
    def list_products(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        sku: Optional[str] = None,
        ean: Optional[str] = None,
        brand: Optional[str] = None,
        category_id: Optional[int] = None,
        manufacturer_id: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        sort_by: str = "id",
        sort_order: str = "asc"
    ) -> Tuple[List[Product], int]:
        """Query products with filtering, search, and pagination."""
        stmt = select(Product)

        if category_id is not None:
            stmt = stmt.join(ProductCategory, ProductCategory.product_id == Product.id).where(
                ProductCategory.category_id == category_id
            )

        conditions = []
        if search:
            kw = f"%{search}%"
            conditions.append(
                or_(
                    Product.title.ilike(kw),
                    Product.sku.ilike(kw),
                    Product.ean.ilike(kw),
                    Product.brand_name.ilike(kw),
                    Product.description.ilike(kw)
                )
            )
        if sku:
            conditions.append(Product.sku == sku)
        if ean:
            conditions.append(Product.ean == ean)
        if brand:
            conditions.append(Product.brand_name.ilike(f"%{brand}%"))
        if manufacturer_id is not None:
            conditions.append(Product.manufacturer_id == manufacturer_id)
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        if max_price is not None:
            conditions.append(Product.price <= max_price)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Total count
        count_stmt = select(func.count(func.distinct(Product.id)))
        if category_id is not None:
            count_stmt = count_stmt.join(ProductCategory, ProductCategory.product_id == Product.id).where(
                ProductCategory.category_id == category_id
            )
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))

        total = db.scalar(count_stmt) or 0

        # Sort
        sort_col = getattr(Product, sort_by, Product.id)
        order_fn = desc if sort_order.lower() == "desc" else asc
        stmt = stmt.order_by(order_fn(sort_col))

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        items = list(db.execute(stmt).scalars().all())

        return items, total

    @staticmethod
    def update_product(db: Session, product_id: int, updates: ProductUpdate) -> Optional[Product]:
        prod = db.get(Product, product_id)
        if not prod:
            return None

        update_dict = updates.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            setattr(prod, k, v)

        prod.updated_at = datetime.now(timezone.utc)
        db.flush()
        return prod

    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        prod = db.get(Product, product_id)
        if not prod:
            return False
        db.delete(prod)
        db.flush()
        return True
