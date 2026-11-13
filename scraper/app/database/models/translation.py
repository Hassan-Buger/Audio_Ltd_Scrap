"""Product translation model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base


class ProductTranslation(Base):
    __tablename__ = "product_translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    language = Column(String(10), default="en", nullable=False, index=True)
    title = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    provider = Column(String(100), nullable=True)
    status = Column(String(50), default="completed", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="translations")

    __table_args__ = (
        Index("idx_product_trans_lang", "product_id", "language", unique=True),
    )
