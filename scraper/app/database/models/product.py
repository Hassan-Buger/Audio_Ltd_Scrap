"""Product, product specification, and price history models."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Numeric, Text, JSON, Index
)
from sqlalchemy.orm import relationship
from .base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_url = Column(String(1024), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    sku = Column(String(100), nullable=True, index=True)
    ean = Column(String(100), nullable=True, index=True)
    model = Column(String(100), nullable=True, index=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id", ondelete="SET NULL"), nullable=True, index=True)
    brand_name = Column(String(255), nullable=True, index=True)
    
    price = Column(Numeric(10, 2), nullable=True)
    regular_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="EUR", nullable=False)
    availability = Column(String(255), nullable=True)
    in_stock = Column(Boolean, nullable=True)
    
    description = Column(Text, nullable=True)
    images = Column(JSON, default=list, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    manufacturer = relationship("Manufacturer", back_populates="products")
    categories = relationship("Category", secondary="product_categories", back_populates="products")
    specifications = relationship("ProductSpecification", back_populates="product", cascade="all, delete-orphan")
    sources = relationship("ProductSource", back_populates="product", cascade="all, delete-orphan")
    translations = relationship("ProductTranslation", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_products_sku_brand", "sku", "brand_name"),
    )


class ProductSpecification(Base):
    __tablename__ = "product_specifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=False)
    numeric_value = Column(Numeric(12, 4), nullable=True)
    unit = Column(String(50), nullable=True)

    product = relationship("Product", back_populates="specifications")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    regular_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="EUR", nullable=False)
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="price_history")
