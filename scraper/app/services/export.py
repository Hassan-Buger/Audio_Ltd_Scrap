"""CSV and JSON export services."""
import csv
import io
import json
from decimal import Decimal
from typing import Generator, Optional
from sqlalchemy.orm import Session
from app.database.models.product import Product
from app.database.models.category import Category
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.category_repo import CategoryRepository


class ExportService:
    @staticmethod
    def export_products_csv(
        db: Session,
        category_id: Optional[int] = None,
        manufacturer_id: Optional[int] = None,
        job_id: Optional[int] = None
    ) -> Generator[str, None, None]:
        """Stream products as CSV rows."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        headers = [
            "id", "title", "sku", "ean", "model", "brand_name",
            "price", "regular_price", "currency", "availability", "in_stock",
            "canonical_url", "is_complete", "specifications_count"
        ]
        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Query products
        products, _ = ProductRepository.list_products(
            db, page=1, page_size=10000,
            category_id=category_id,
            manufacturer_id=manufacturer_id
        )

        for p in products:
            row = [
                p.id,
                p.title,
                p.sku or "",
                p.ean or "",
                p.model or "",
                p.brand_name or "",
                str(p.price) if p.price is not None else "",
                str(p.regular_price) if p.regular_price is not None else "",
                p.currency,
                p.availability or "",
                "true" if p.in_stock else "false" if p.in_stock is False else "",
                p.canonical_url,
                "true" if p.is_complete else "false",
                len(p.specifications) if p.specifications else 0
            ]
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    @staticmethod
    def export_products_json(
        db: Session,
        category_id: Optional[int] = None,
        manufacturer_id: Optional[int] = None,
        job_id: Optional[int] = None
    ) -> Generator[str, None, None]:
        """Stream products as JSON array."""
        yield "[\n"
        products, _ = ProductRepository.list_products(
            db, page=1, page_size=10000,
            category_id=category_id,
            manufacturer_id=manufacturer_id
        )
        first = True
        for p in products:
            item = {
                "id": p.id,
                "title": p.title,
                "sku": p.sku,
                "ean": p.ean,
                "model": p.model,
                "brand_name": p.brand_name,
                "price": float(p.price) if p.price is not None else None,
                "regular_price": float(p.regular_price) if p.regular_price is not None else None,
                "currency": p.currency,
                "availability": p.availability,
                "in_stock": p.in_stock,
                "canonical_url": p.canonical_url,
                "description": p.description,
                "images": p.images,
                "is_complete": p.is_complete,
                "specifications": [
                    {
                        "label": s.label,
                        "value": s.value,
                        "numeric_value": float(s.numeric_value) if s.numeric_value is not None else None,
                        "unit": s.unit
                    }
                    for s in p.specifications
                ]
            }
            prefix = "" if first else ",\n"
            first = False
            yield prefix + json.dumps(item, ensure_ascii=False, indent=2)
        yield "\n]"

    @staticmethod
    def export_categories_json(db: Session) -> str:
        """Export categories tree as JSON string."""
        tree = CategoryRepository.get_tree(db)
        return json.dumps([n.model_dump() for n in tree], default=str, ensure_ascii=False, indent=2)
