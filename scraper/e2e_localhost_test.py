"""
End-to-end localhost verification test runner.
Tests every API endpoint, dashboard page, job control, HTML ingestion,
and data export against the live running instance at http://localhost:8000.
"""
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

from app.config import settings

BASE_URL = "http://localhost:8000"
API_KEY = settings.API_KEY

tests_run = 0
tests_passed = 0
failures = []

def test(name):
    def decorator(fn):
        global tests_run, tests_passed, failures
        tests_run += 1
        try:
            fn()
            tests_passed += 1
            print(f"  [PASS] {name}", flush=True)
        except Exception as e:
            failures.append((name, str(e)))
            print(f"  [FAIL] {name}: {e}", flush=True)
    return decorator

def http_get(path, headers=None):
    h = headers or {}
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

def http_post_json(path, data, headers=None):
    h = headers or {}
    h["Content-Type"] = "application/json"
    h["X-API-Key"] = API_KEY
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

def http_post_form(path, form_data):
    url = f"{BASE_URL}{path}"
    body = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")


print("=" * 65, flush=True)
print("  AUDIONVIDEO.LT SCRAPER - COMPLETE LOCALHOST E2E VERIFICATION", flush=True)
print("=" * 65, flush=True)
print(f"Target: {BASE_URL} | Time: {datetime.now().isoformat()}\n", flush=True)

# --- 1. Health & System Checks ---
print("[1] Health & System Status Endpoints", flush=True)

@test("GET /health")
def t1():
    status, body = http_get("/health")
    assert status == 200
    data = json.loads(body)
    assert data["status"] == "ok"
    assert data["service"] == "audiovideo-scraper"

@test("GET /ready")
def t2():
    status, body = http_get("/ready")
    assert status == 200
    data = json.loads(body)
    assert data["status"] == "ready"
    assert data["database"] == "connected"

@test("GET /api/v1/health")
def t3():
    status, body = http_get("/api/v1/health")
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert data["data"]["status"] == "ok"

@test("GET /api/v1/health/ready")
def t4():
    status, body = http_get("/api/v1/health/ready")
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert data["data"]["database"] == "up"

@test("GET /api/v1/system/status")
def t5():
    status, body = http_get("/api/v1/system/status")
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert data["data"]["status"] == "operational"

@test("GET /api/v1/system/stats")
def t6():
    status, body = http_get("/api/v1/system/stats")
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert "total_products" in data["data"]


# --- 2. Dashboard UI Pages ---
print("\n[2] Operator Dashboard Routes (HTML Rendering)", flush=True)

@test("GET /dashboard (Overview)")
def t7():
    status, html = http_get("/dashboard")
    assert status == 200
    assert "<title>Overview - Audiovideo.lt Console</title>" in html
    assert "Catalogue Operations Overview" in html

@test("GET /dashboard/jobs (Jobs Management)")
def t8():
    status, html = http_get("/dashboard/jobs")
    assert status == 200
    assert "Crawl & Scraping Jobs" in html
    assert "Cloudflare Clearance Session Cookie" in html
    assert "Ingest Saved HTML Page" in html

@test("GET /dashboard/products (Products Explorer)")
def t9():
    status, html = http_get("/dashboard/products")
    assert status == 200
    assert "Product Catalogue" in html
    assert "Garso izoliacija" in html

@test("GET /dashboard/categories (Categories Tree)")
def t10():
    status, html = http_get("/dashboard/categories")
    assert status == 200
    assert "Category Tree & Coverage" in html

@test("GET /dashboard/failures (Failure Triage)")
def t11():
    status, html = http_get("/dashboard/failures")
    assert status == 200
    assert "Failures & Inaccessible URLs" in html

@test("GET /dashboard/reports (Reports & Exports)")
def t12():
    status, html = http_get("/dashboard/reports")
    assert status == 200
    assert "Reports & Data Quality" in html

@test("GET /docs (Swagger OpenAPI UI)")
def t13():
    status, html = http_get("/docs")
    assert status == 200
    assert "SwaggerUIBundle" in html

@test("GET /static/css/styles.css (Static Asset Tokens)")
def t14():
    status, css = http_get("/static/css/styles.css")
    assert status == 200
    assert "--color-bg" in css
    assert "--color-accent" in css
    assert "--font-sans" in css


# --- 3. Scraper Control, Ingestion & Frontier ---
print("\n[3] Scraping Control, Ingestion & Frontier Execution", flush=True)

@test("POST /dashboard/settings/cookies (Set & Update Cookie)")
def t15():
    status, _ = http_post_form("/dashboard/settings/cookies", {"cookies": "cf_clearance=e2e_verified_token_12345"})
    assert status == 200
    _, html = http_get("/dashboard/jobs")
    assert "e2e_verified_token_12345" in html
    assert "Active (Cookie Configured)" in html

@test("POST /api/v1/scraping/ingest-html (Direct HTML Ingestion)")
def t16():
    test_html = """<!doctype html>
    <html lang="lt">
    <head>
      <title>Test Midrange Woofer</title>
      <link rel="canonical" href="https://www.audiovideo.lt/test-midrange-woofer.html">
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Test Midrange Woofer 165mm",
        "sku": "E2E-TEST-001",
        "gtin13": "4790000000999",
        "brand": {"@type": "Brand", "name": "Audison"},
        "description": "Aukštos kokybės 165 mm garsiakalbiai.",
        "offers": {"@type": "Offer", "price": "199.00", "priceCurrency": "EUR", "availability": "https://schema.org/InStock"}
      }
      </script>
    </head>
    <body>
      <div class="product-info-main"><h1>Test Midrange Woofer 165mm</h1></div>
      <table id="product-attribute-specs-table">
        <tr><th>Galia</th><td>150 W</td></tr>
        <tr><th>Varža</th><td>4 Ohm</td></tr>
      </table>
    </body>
    </html>"""
    payload = {
        "url": "https://www.audiovideo.lt/test-midrange-woofer.html",
        "html": test_html,
        "final_url": "https://www.audiovideo.lt/test-midrange-woofer.html"
    }
    status, body = http_post_json("/api/v1/scraping/ingest-html", payload)
    assert status == 201
    res = json.loads(body)
    assert res["success"] is True
    assert "job_id" in res["data"]

@test("POST /api/v1/scraping/start (Dispatch Seeded Crawl Job)")
def t17():
    payload = {
        "scope": "full",
        "seed_urls": ["https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1"]
    }
    status, body = http_post_json("/api/v1/scraping/start", payload)
    assert status in (200, 202)
    res = json.loads(body)
    assert res["success"] is True
    assert "job_id" in res["data"]


# --- 4. Products & Catalog API ---
print("\n[4] Catalog & Product Queries", flush=True)

@test("GET /api/v1/products (List Products)")
def t18():
    status, body = http_get("/api/v1/products")
    assert status == 200
    res = json.loads(body)
    assert res["success"] is True
    assert res["meta"]["total"] >= 1
    skus = [p["sku"] for p in res["data"]]
    assert "E2E-TEST-001" in skus or "ab 12 345" in skus

@test("GET /api/v1/products/sku/E2E-TEST-001 (Lookup by SKU)")
def t19():
    status, body = http_get("/api/v1/products/sku/E2E-TEST-001")
    assert status == 200
    res = json.loads(body)
    assert res["success"] is True
    assert res["data"]["sku"] == "E2E-TEST-001"
    assert res["data"]["brand_name"] == "Audison"
    assert float(res["data"]["price"]) == 199.0

@test("GET /api/v1/search/products (Search Catalog by keyword 'q')")
def t20():
    status, body = http_get("/api/v1/search/products?q=Audison")
    assert status == 200
    res = json.loads(body)
    assert res["success"] is True
    assert len(res["data"]) >= 1


# --- 5. Data Exports & Reports ---
print("\n[5] Data Exports & Reporting", flush=True)

@test("GET /api/v1/exports/products/csv (CSV Export Streaming)")
def t21():
    status, csv_data = http_get("/api/v1/exports/products/csv")
    assert status == 200
    assert "id,title,sku,ean" in csv_data
    assert "E2E-TEST-001" in csv_data or "ab 12 345" in csv_data

@test("GET /api/v1/exports/products/json (JSON Export Streaming Array)")
def t22():
    status, json_data = http_get("/api/v1/exports/products/json")
    assert status == 200
    res = json.loads(json_data)
    assert isinstance(res, list)
    assert len(res) >= 1

@test("GET /api/v1/reports/overview (Overview Report)")
def t23():
    status, body = http_get("/api/v1/reports/overview")
    assert status == 200
    res = json.loads(body)
    assert res["success"] is True
    assert res["data"]["total_products"] >= 1

@test("GET /api/v1/reports/coverage (Coverage Report)")
def t24():
    status, body = http_get("/api/v1/reports/coverage")
    assert status == 200
    res = json.loads(body)
    assert res["success"] is True

@test("GET /api/v1/reports/completeness (Completeness Report)")
def t25():
    status, body = http_get("/api/v1/reports/completeness")
    assert status == 200
    res = json.loads(body)
    assert res["success"] is True


print("\n" + "=" * 65, flush=True)
print(f"  TEST RESULTS: {tests_passed}/{tests_run} Passed ({int(tests_passed/tests_run*100)}%)", flush=True)
if failures:
    print(f"  FAILURES ({len(failures)}):", flush=True)
    for name, err in failures:
        print(f"    - {name}: {err}", flush=True)
    sys.exit(1)
else:
    print("  ALL 25/25 ENDPOINTS, DASHBOARDS, INGESTION & EXPORTS VERIFIED OK!", flush=True)
print("=" * 65, flush=True)
