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
    assert prod["specifications_count"] >= 2

    # 2. Verify snapshot appears in GET /api/v1/scraping/snapshots
    snap_resp = client.get("/api/v1/scraping/snapshots")
    assert snap_resp.status_code == 200
    snaps = snap_resp.json()["data"]
    assert len(snaps) >= 1
    found = any(s["url"] == payload["url"] for s in snaps)
    assert found is True
