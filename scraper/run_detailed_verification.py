"""Comprehensive in-depth verification of Audiovideo.lt backend scraping system."""
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import hashlib
from pathlib import Path
from decimal import Decimal

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-operator-api-key-change-in-production"
AUTH_HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def request_json(method, path, body=None, headers=None):
    url = f"{BASE_URL}{path}"
    h = headers if headers is not None else AUTH_HEADERS
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, {"raw": content}

def request_raw(method, path, headers=None):
    url = f"{BASE_URL}{path}"
    h = headers if headers is not None else AUTH_HEADERS
    req = urllib.request.Request(url, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), e.headers


print("=" * 75)
print("  AUDIONVIDEO.LT BACKEND - IN-DEPTH VERIFICATION & TEST REPORT")
print("=" * 75)
print(f"Target Server: {BASE_URL}")

total_tests = 0
passed_tests = 0

def record_test(name, success, details=""):
    global total_tests, passed_tests
    total_tests += 1
    if success:
        passed_tests += 1
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} - {details}")

# =====================================================================
# SUITE 1: Snapshot-First Extraction & Disk Cache Lifecycle
# =====================================================================
print("\n--- [SUITE 1] Snapshot-First Extraction & Disk Persistence ---")

product_url = "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/stp-bomb-aero-vibro-izoliacija.html"
product_html = """<!DOCTYPE html>
<html lang="lt">
<head>
  <meta charset="UTF-8">
  <title>STP Bomb Aero Vibroizoliacija 4.2mm - audiovideo.lt</title>
  <link rel="canonical" href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/stp-bomb-aero-vibro-izoliacija.html" />
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "STP Bomb Aero Vibroizoliacija 4.2mm",
    "sku": "STP-BOMB-42",
    "gtin13": "4790000009999",
    "brand": {
      "@type": "Brand",
      "name": "Standartplast"
    },
    "offers": {
      "@type": "Offer",
      "price": "84.90",
      "priceCurrency": "EUR",
      "availability": "https://schema.org/InStock"
    },
    "description": "Profesionali daugiasluoksnė vibroizoliacija automobilių ratų arkoms ir dugnui.",
    "image": [
      "https://www.audiovideo.lt/media/catalog/product/s/t/stp_bomb_aero_1.jpg",
      "https://www.audiovideo.lt/media/catalog/product/s/t/stp_bomb_aero_2.jpg"
    ]
  }
  </script>
</head>
<body>
  <div class="product-info-main">
    <h1 class="page-title">STP Bomb Aero Vibroizoliacija 4.2mm</h1>
  </div>
  <table class="data table additional-attributes">
    <tbody>
      <tr><th>Storis</th><td>4.2 mm</td></tr>
      <tr><th>Lapų skaičius</th><td>5 vnt</td></tr>
      <tr><th>Pakuotės plotas</th><td>2.0 m²</td></tr>
      <tr><th>Mechaninių nuostolių koeficientas (MLF)</th><td>0.60</td></tr>
      <tr><th>Darbinė temperatūra</th><td>nuo -45°C iki +100°C</td></tr>
    </tbody>
  </table>
</body>
</html>
"""

# 1.1 Ingest & Save Snapshot
status, res = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {
    "url": product_url,
    "html_content": product_html,
    "force_refresh": True
})

record_test(
    "1.1 Ingest HTML snapshot via POST /api/v1/scraping/snapshot-and-scrape",
    status == 200 and res.get("success") is True,
    f"Status: {status}, Response: {res}"
)

# 1.2 Verify disk snapshot file
snapshot_path = res.get("data", {}).get("snapshot_file")
has_file = snapshot_path and os.path.exists(snapshot_path)
record_test(
    f"1.2 Physical HTML snapshot exists on disk ({snapshot_path})",
    has_file,
    f"Path: {snapshot_path}"
)

if has_file:
    stored_text = Path(snapshot_path).read_text(encoding="utf-8")
    record_test(
        f"1.3 Snapshot content integrity (valid HTML snapshot saved)",
        "STP Bomb Aero Vibroizoliacija 4.2mm" in stored_text and "<table" in stored_text,
        f"Snapshot length: {len(stored_text)}"
    )

# 1.4 Verify extracted fields
prod_data = res.get("data", {}).get("product", {})
specs = {s["label"]: s["value"] for s in prod_data.get("specifications", [])}

record_test(
    "1.4 Extracted Core Product Identifiers (Title, SKU, EAN, Brand, Price)",
    prod_data.get("title") == "STP Bomb Aero Vibroizoliacija 4.2mm" and
    prod_data.get("sku") == "STP-BOMB-42" and
    prod_data.get("ean") == "4790000009999" and
    prod_data.get("brand") == "Standartplast" and
    prod_data.get("price") == 84.90 and
    prod_data.get("currency") == "EUR" and
    prod_data.get("in_stock") is True,
    f"Prod data: {prod_data}"
)

record_test(
    "1.5 Preserved Lithuanian Specifications intact (Storis, MLF, Darbinė temperatūra)",
    specs.get("Storis") == "4.2 mm" and
    specs.get("Pakuotės plotas") == "2.0 m²" and
    "Darbinė temperatūra" in specs,
    f"Specs: {specs}"
)

# 1.6 Verify Cache Replay (load from disk without network fetch)
status_cache, res_cache = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {
    "url": product_url,
    "force_refresh": False
})

record_test(
    "1.6 Disk Cache Replay (is_cached_replay == True, instant reload)",
    status_cache == 200 and res_cache.get("data", {}).get("is_cached_replay") is True,
    f"Response: {res_cache}"
)

# 1.7 Category Listing Page Snapshot & Discovery
category_url = "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1"
category_html = """<!DOCTYPE html>
<html lang="lt">
<head>
  <title>Garso izoliacija automobiliams - audiovideo.lt</title>
</head>
<body>
  <div class="category-view">
    <ol class="products list items product-items">
      <li class="item product product-item">
        <a class="product-item-link" href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/standartplast-stp-gold-bulk-pack.html">STP Gold 2.3mm</a>
        <span class="price">69,50 €</span>
      </li>
      <li class="item product product-item">
        <a class="product-item-link" href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/stp-bomb-aero-vibro-izoliacija.html">STP Bomb Aero</a>
        <span class="price">84,90 €</span>
      </li>
    </ol>
    <ul class="pages-items">
      <li class="item current"><strong>1</strong></li>
      <li class="item"><a href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=2" class="page">2</a></li>
      <li class="item pages-item-next"><a href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=2" class="action next">Next</a></li>
    </ul>
  </div>
</body>
</html>
"""

status_cat, res_cat = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {
    "url": category_url,
    "html_content": category_html,
    "force_refresh": True
})

cat_data = res_cat.get("data", {})
record_test(
    "1.7 Category page ingestion & pagination discovery",
    status_cat == 200 and
    cat_data.get("page_type") == "category_listing" and
    cat_data.get("products_found_count") >= 2 and
    cat_data.get("pagination", {}).get("total_pages") >= 2,
    f"Cat data: {cat_data}"
)

# 1.8 Snapshot Inventory List
status_snaps, res_snaps = request_json("GET", "/api/v1/scraping/snapshots")
snaps = res_snaps.get("data", [])
record_test(
    f"1.8 GET /api/v1/scraping/snapshots lists saved snapshots ({len(snaps)} files tracked)",
    status_snaps == 200 and len(snaps) >= 1 and any(s["url"] == product_url for s in snaps),
    f"Count: {len(snaps)}"
)


# =====================================================================
# SUITE 2: Conservative Deduplication & Price History Tracking
# =====================================================================
print("\n--- [SUITE 2] Deduplication & Price History Tracking ---")

# 2.1 Re-ingest with updated price (same SKU / EAN)
updated_html = product_html.replace('"price": "84.90"', '"price": "79.99"')
status_upd, res_upd = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {
    "url": product_url,
    "html_content": updated_html,
    "force_refresh": True
})

upd_prod = res_upd.get("data", {}).get("product", {})
record_test(
    "2.1 Upsert existing product by SKU/EAN (is_new_product == False, updated price to 79.99 EUR)",
    status_upd == 200 and
    res_upd.get("data", {}).get("is_new_product") is False and
    upd_prod.get("price") == 79.99,
    f"Response: {res_upd}"
)

# 2.2 Protect Variants: Ingest distinct variant with unique SKU, EAN and canonical URL
variant_url = "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/stp-bomb-aero-vibro-izoliacija-bulk.html"
variant_html = (
    product_html
    .replace('STP-BOMB-42', 'STP-BOMB-BULK-10')
    .replace('4790000009999', '4790000009998')
    .replace('4.2mm', 'Bulk Pack 10 Sheets')
    .replace('href="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/stp-bomb-aero-vibro-izoliacija.html"', f'href="{variant_url}"')
)

status_var, res_var = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {
    "url": variant_url,
    "html_content": variant_html,
    "force_refresh": True
})

var_prod = res_var.get("data", {}).get("product", {})
record_test(
    "2.2 Variant Protection: Ingest distinct SKU maintains independent product row (ID != base ID)",
    status_var == 200 and
    var_prod.get("sku") == "STP-BOMB-BULK-10" and
    var_prod.get("id") != prod_data.get("id"),
    f"Base ID: {prod_data.get('id')}, Variant ID: {var_prod.get('id')}"
)


# =====================================================================
# SUITE 3: Catalog Queries, Search & Streaming Exports
# =====================================================================
print("\n--- [SUITE 3] Catalog Queries, Search & Streaming Exports ---")

# 3.1 Lookup by SKU
status_sku, res_sku = request_json("GET", "/api/v1/products/sku/STP-BOMB-42")
record_test(
    "3.1 GET /api/v1/products/sku/STP-BOMB-42 (Fast indexed lookup)",
    status_sku == 200 and res_sku.get("data", {}).get("sku") == "STP-BOMB-42",
    f"SKU response: {res_sku}"
)

# 3.2 Full-text / Keyword Search
status_srch, res_srch = request_json("GET", "/api/v1/search/products?q=Standartplast")
srch_items = res_srch.get("data", []) if isinstance(res_srch.get("data"), list) else []
record_test(
    f"3.2 GET /api/v1/search/products?q=Standartplast ({len(srch_items)} matches)",
    status_srch == 200 and len(srch_items) >= 2,
    f"Search matches: {len(srch_items)}"
)

# 3.3 CSV Export Streaming
status_csv, csv_body, csv_headers = request_raw("GET", "/api/v1/exports/products/csv")
csv_lines = [l for l in csv_body.splitlines() if l.strip()]
record_test(
    f"3.3 GET /api/v1/exports/products/csv (Streaming CSV, {len(csv_lines)} rows)",
    status_csv == 200 and "text/csv" in csv_headers.get("Content-Type", "") and "title,sku,ean" in csv_lines[0].lower(),
    f"Header: {csv_lines[0] if csv_lines else 'None'}"
)

# 3.4 JSON Export Streaming
status_json, json_body, json_headers = request_raw("GET", "/api/v1/exports/products/json")
parsed_json = json.loads(json_body) if status_json == 200 else []
record_test(
    f"3.4 GET /api/v1/exports/products/json (Streaming JSON, {len(parsed_json)} products)",
    status_json == 200 and isinstance(parsed_json, list) and len(parsed_json) >= 4,
    f"Count: {len(parsed_json)}"
)


# =====================================================================
# SUITE 4: Security, Authentication & Error Handling
# =====================================================================
print("\n--- [SUITE 4] Security, Authentication & Error Handling ---")

# 4.1 Unauthorized request rejection (No API key)
status_unauth, res_unauth = request_json(
    "POST", "/api/v1/scraping/snapshot-and-scrape",
    {"url": "https://www.audiovideo.lt/test.html"},
    headers={"Content-Type": "application/json"}  # No X-API-Key
)
record_test(
    "4.1 Authentication Gate: 401 Unauthorized when API Key is missing",
    status_unauth == 401 and res_unauth.get("detail", {}).get("code") == "UNAUTHORIZED",
    f"Status: {status_unauth}, Detail: {res_unauth}"
)

# 4.2 Malformed Payload Validation
status_bad, res_bad = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {})  # Missing 'url'
record_test(
    "4.2 Schema Validation: 422 Unprocessable Entity on missing required field",
    status_bad == 422,
    f"Status: {status_bad}"
)

# 4.3 Non-existent SKU lookup
status_404, res_404 = request_json("GET", "/api/v1/products/sku/NON-EXISTENT-SKU-999")
record_test(
    "4.3 Resource Lookup: 404 Not Found on invalid SKU",
    status_404 == 404,
    f"Status: {status_404}"
)

# 4.4 Cloudflare Challenge Handling (Live URL fetch without cookie)
status_cf, res_cf = request_json("POST", "/api/v1/scraping/snapshot-and-scrape", {
    "url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija/naujas-produktas.html",
    "force_refresh": True
})
record_test(
    "4.4 Live Cloudflare Handling: Returns 403 with ACCESS_RESTRICTED and actionable guidance",
    status_cf == 403 and res_cf.get("detail", {}).get("code") == "ACCESS_RESTRICTED",
    f"Status: {status_cf}, Code: {res_cf.get('detail', {}).get('code')}"
)


print("\n" + "=" * 75)
print(f"  FINAL VERIFICATION SCORE: {passed_tests}/{total_tests} Tests Passed ({(passed_tests/total_tests)*100:.1f}%)")
print("=" * 75)
