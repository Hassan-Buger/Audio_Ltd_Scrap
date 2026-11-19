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
    assert prod.description == "Aukščiausios klasės Mille Legend serijos vidutinių dažnių garsiakalbiai automobiliui."
    assert len(prod.specifications) == 3

    labels = [s.label for s in prod.specifications]
    assert "Maksimali galia" in labels
    assert "Varža" in labels


def test_extract_product_dom_description():
    """Test DOM description extraction from Magento 2 product attribute description block."""
    html = """
    <!doctype html>
    <html>
    <head><title>Test Item</title></head>
    <body>
      <h1 class="page-title">Garso izoliacija B</h1>
      <div class="product-info-stock-sku"><div class="sku">SKU-99</div></div>
      <div class="price-box"><span class="price">120.00 €</span></div>
      <div class="product attribute description">
        Stiprinimo <b>sistema</b>, skirta automobilių garso izoliacijai ir vibroizoliacijai.
      </div>
    </body>
    </html>
    """
    prod = extract_product_detail(html, "https://www.audiovideo.lt/prod-test.html")
    assert prod is not None
    assert prod.title == "Garso izoliacija B"
    assert prod.description == "Stiprinimo sistema, skirta automobilių garso izoliacijai ir vibroizoliacijai."


def test_extract_product_magento1_description():
    """Test DOM description extraction from Magento 1 standard tabs/boxes."""
    html = """
    <!doctype html>
    <html>
    <head><title>Test Item M1</title></head>
    <body>
      <h1 class="product-name">Test Prekė</h1>
      <div class="price-box"><span class="price">45.00 €</span></div>
      <div id="product_tabs_description_contents">
        <div class="std">
          Kokybiška bituminė danga garso slopinimui automobilyje.
        </div>
      </div>
    </body>
    </html>
    """
    prod = extract_product_detail(html, "https://www.audiovideo.lt/prod-m1.html")
    assert prod is not None
    assert prod.description == "Kokybiška bituminė danga garso slopinimui automobilyje."
