"""Optional translation service for creating English translations without modifying source records."""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.config import settings
from app.database.models.product import Product
from app.database.models.translation import ProductTranslation
from app.schemas.translation import TranslationStatusResponse


class TranslationService:
    @staticmethod
    def get_status(db: Session) -> TranslationStatusResponse:
        total = db.scalar(select(func.count(Product.id))) or 0
        translated = db.scalar(select(func.count(ProductTranslation.id))) or 0
        pending = max(0, total - translated)
        cov = (translated / total * 100.0) if total > 0 else 0.0

        return TranslationStatusResponse(
            enabled=settings.TRANSLATION_ENABLED,
            provider=settings.TRANSLATION_PROVIDER,
            total_products=total,
            translated_products=translated,
            pending_products=pending,
            failed_translations=0,
            coverage_percentage=round(cov, 2)
        )

    @staticmethod
    def translate_product(
        db: Session,
        product_id: int,
        target_lang: str = "en",
        provider: str = "mock"
    ) -> Optional[ProductTranslation]:
        """
        Create or update an independent translation record.
        Original Lithuanian title and description remain intact on the Product model.
        """
        prod = db.get(Product, product_id)
        if not prod:
            return None

        # Check existing translation
        stmt = select(ProductTranslation).where(
            and_(
                ProductTranslation.product_id == product_id,
                ProductTranslation.language == target_lang
            )
        )
        trans = db.execute(stmt).scalar_one_or_none()

        # Generate translation content without altering Lithuanian source
        translated_title = f"[EN] {prod.title}" if prod.title else None
        translated_desc = f"[Translated to English]: {prod.description}" if prod.description else None

        now = datetime.now(timezone.utc)
        if trans:
            trans.title = translated_title
            trans.description = translated_desc
            trans.provider = provider
            trans.status = "completed"
        else:
            trans = ProductTranslation(
                product_id=product_id,
                language=target_lang,
                title=translated_title,
                description=translated_desc,
                provider=provider,
                status="completed",
                created_at=now
            )
            db.add(trans)

        db.flush()
        return trans
