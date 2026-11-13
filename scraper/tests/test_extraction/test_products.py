"""Tests for product detail extraction from JSON-LD and HTML DOM."""
from decimal import Decimal
from app.extraction.products import extract_product_detail


def test_extract_product_detail(sample_product_html):
    prod = extract_product_detail(
        sample_product_html,
        "https://www.audiovideo.lt/hertz-ml-700-set-midrange"
    )
    assert prod is not None
    assert prod.title == "Hertz ML 700.3 Legend"
    assert prod.sku == "ML-700-3"
    assert prod.ean == "8018823113423"
    assert prod.brand_name == "Hertz"
    assert prod.price == Decimal("349.00")
    assert prod.currency == "EUR"
    assert prod.canonical_url == "https://www.audiovideo.lt/hertz-ml-700-set-midrange"
    assert prod.is_complete is True
    assert len(prod.specifications) == 3

    labels = [s.label for s in prod.specifications]
    assert "Maksimali galia" in labels
    assert "Varža" in labels
