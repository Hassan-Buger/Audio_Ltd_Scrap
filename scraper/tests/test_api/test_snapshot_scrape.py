"""Test snapshot-and-scrape backend API endpoint."""
from unittest.mock import patch, MagicMock


def test_snapshot_and_scrape_with_html_content(client, auth_headers):
    sample_html = """
    <!DOCTYPE html>
    <html lang="lt">
    <head>
      <title>Test STP Black Silver Garso Izoliacija - audiovideo.lt</title>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "STP Black Silver Garso Izoliacija 2mm",
        "sku": "STP-BS-2MM",
        "mpn": "STP-BS-2MM",
        "gtin13": "4790000008888",
        "brand": {
          "@type": "Brand",
          "name": "Standartplast"
        },
        "offers": {
          "@type": "Offer",
          "price": "55.00",
          "priceCurrency": "EUR",
          "availability": "https://schema.org/InStock"
        },
        "description": "Profesionali vibroizoliacinė medžiaga automobiliams."
      }
      </script>
    </head>
    <body>
      <div class="product-info-main">
        <h1 class="page-title">STP Black Silver Garso Izoliacija 2mm</h1>
      </div>
      <table class="data table additional-attributes">
        <tbody>
          <tr><th>Storis</th><td>2 mm</td></tr>
          <tr><th>Pakuotės plotas</th><td>4.5 m²</td></tr>
        </tbody>
      </table>
    </body>
    </html>
    """

    payload = {
        "url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/standartplast-stp-black-silver-bulk-pack.html",
        "html_content": sample_html,
        "force_refresh": True
    }

    # 1. Call snapshot-and-scrape endpoint
    resp = client.post("/api/v1/scraping/snapshot-and-scrape", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    # Verify snapshot was saved to disk
    assert data["snapshot_saved"] is True
    assert data["snapshot_file"] is not None
    assert data["snapshot_size_bytes"] > 0
    assert data["page_type"] == "product"

    # Verify extracted product details
    prod = data["product"]
    assert prod["title"] == "STP Black Silver Garso Izoliacija 2mm"
    assert prod["sku"] == "STP-BS-2MM"
    assert prod["ean"] == "4790000008888"
    assert prod["brand"] == "Standartplast"
    assert prod["price"] == 55.00
    assert prod["currency"] == "EUR"
    assert prod["in_stock"] is True
    assert prod["description"] == "Profesionali vibroizoliacinė medžiaga automobiliams."
    assert prod["specifications_count"] >= 2

    # 2. Verify snapshot appears in GET /api/v1/scraping/snapshots
    snap_resp = client.get("/api/v1/scraping/snapshots")
    assert snap_resp.status_code == 200
    snaps = snap_resp.json()["data"]
    assert len(snaps) >= 1
    found = any(s["url"] == payload["url"] for s in snaps)
    assert found is True


def test_snapshot_and_scrape_category_listing(client, auth_headers):
    category_html = """
    <!DOCTYPE html>
    <html lang="lt">
    <head><title>Garso izoliacija - audiovideo.lt</title></head>
    <body>
      <div class="category-description std">
        Aukščiausios kokybės automobilių garso ir vibro izoliacinės medžiagos.
      </div>
      <ul class="products-grid">
        <li class="item">
          <h2 class="product-name">
            <a href="https://www.audiovideo.lt/item-1.html">BOOM 10 Akustinis porolonas</a>
          </h2>
          <div class="price-box"><span class="price">3.00 €</span></div>
        </li>
        <li class="item">
          <h2 class="product-name">
            <a href="https://www.audiovideo.lt/item-2.html">STP Black Silver 2mm</a>
          </h2>
          <div class="price-box"><span class="price">8.50 €</span></div>
        </li>
      </ul>
      <div class="pages">
        <ol class="pagination">
          <li class="current">1</li>
          <li><a href="https://www.audiovideo.lt/garso-izoliacija?p=2">2</a></li>
        </ol>
      </div>
    </body>
    </html>
    """
    payload = {
        "url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija",
        "html_content": category_html,
        "force_refresh": True
    }
    resp = client.post("/api/v1/scraping/snapshot-and-scrape", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    assert data["page_type"] == "category_listing"
    assert data["category_description"] == "Aukščiausios kokybės automobilių garso ir vibro izoliacinės medžiagos."
    assert data["products_found_count"] == 2
    assert len(data["products"]) == 2
    assert data["products"][0]["title"] == "BOOM 10 Akustinis porolonas"
    assert data["products"][0]["price"] == 3.00
    assert data["products"][1]["title"] == "STP Black Silver 2mm"
    assert data["products"][1]["price"] == 8.50
