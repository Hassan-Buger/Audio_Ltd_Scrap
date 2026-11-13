"""Tests for conservative product deduplication and provenance retention."""
from decimal import Decimal
from app.schemas.product import ProductCreate
from app.database.repositories.product_repo import ProductRepository
from app.database.models.product import Product


def test_product_deduplication_by_ean(db):
    p1 = ProductCreate(
        canonical_url="https://www.audiovideo.lt/hertz-ml700-url1",
        title="Hertz ML 700 Set",
        sku="ML-700",
        ean="8018823113423",
        brand_name="Hertz",
        price=Decimal("349.00"),
        source_url="https://www.audiovideo.lt/cat1"
    )
    prod1, is_new1 = ProductRepository.upsert_product(db, p1)
    db.commit()
    assert is_new1 is True

    # Same EAN discovered through a different category URL with slightly different title
    p2 = ProductCreate(
        canonical_url="https://www.audiovideo.lt/hertz-ml700-url2",
        title="Hertz ML 700.3 Midrange",
        sku="ML-700-DIFF",
        ean="8018823113423",  # same EAN
        brand_name="Hertz",
        price=Decimal("349.00"),
        source_url="https://www.audiovideo.lt/cat2"
    )
    prod2, is_new2 = ProductRepository.upsert_product(db, p2)
    db.commit()
    assert is_new2 is False
    assert prod2.id == prod1.id
    # Ensure both sources retained in provenance
    assert len(prod2.sources) == 2


def test_protect_variants_without_matching_identifiers(db):
    # Two products with similar title but different SKUs and no shared EAN must remain distinct
    p1 = ProductCreate(
        canonical_url="https://www.audiovideo.lt/hertz-hcp-4",
        title="Hertz HCP 4 Amplifier",
        sku="HCP-4",
        brand_name="Hertz",
        price=Decimal("220.00")
    )
    p2 = ProductCreate(
        canonical_url="https://www.audiovideo.lt/hertz-hcp-4d",
        title="Hertz HCP 4D Amplifier",
        sku="HCP-4D",
        brand_name="Hertz",
        price=Decimal("350.00")
    )
    prod1, is_new1 = ProductRepository.upsert_product(db, p1)
    prod2, is_new2 = ProductRepository.upsert_product(db, p2)
    db.commit()

    assert is_new1 is True
    assert is_new2 is True
    assert prod1.id != prod2.id
