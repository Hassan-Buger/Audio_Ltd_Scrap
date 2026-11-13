"""Scrapy pipeline for persisting extracted items into PostgreSQL / SQLite."""
from app.database.session import transaction_scope
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.category_repo import CategoryRepository
from app.schemas.product import ProductCreate
from app.schemas.category import CategoryCreate


class DatabasePipeline:
    def process_item(self, item, spider):
        item_type = item.get("type")
        payload = item.get("item")

        with transaction_scope() as db:
            if item_type == "product" and isinstance(payload, ProductCreate):
                ProductRepository.upsert_product(db, payload)
            elif item_type == "category" and isinstance(payload, CategoryCreate):
                CategoryRepository.upsert_category(db, payload)

        return item
