# Audiovideo.lt Scraper & Operations API — Complete User Guide

Welcome to the complete developer and operator reference manual for the **Audiovideo.lt Product Scraper & Operations API**.

---

## 1. Quick Reference & Base URLs

| Environment | Base URL | Swagger UI (Interactive) | ReDoc (Reference) | OpenAPI Spec |
| :--- | :--- | :--- | :--- | :--- |
| **Production (Railway)** | `https://audioltdscrap-production.up.railway.app` | [`/docs`](https://audioltdscrap-production.up.railway.app/docs) | [`/redoc`](https://audioltdscrap-production.up.railway.app/redoc) | `/openapi.json` |
| **Local Development** | `http://localhost:8000` | [`http://localhost:8000/docs`](http://localhost:8000/docs) | [`http://localhost:8000/redoc`](http://localhost:8000/redoc) | `/openapi.json` |

Root path `/` automatically redirects (`302`) directly to `/docs`.

---

## 2. Authentication & Security

All mutating operations (starting crawls, uploading snapshots, creating exports, triggering translations, editing products) are protected by operator authentication.

The API supports **three distinct authentication methods**:

### Option A: Header `X-API-Key` (Recommended for scripts)
```bash
curl -H "X-API-Key: YOUR_OPERATOR_API_KEY" \
     https://audioltdscrap-production.up.railway.app/api/v1/scraping/status
```

### Option B: Bearer Token in `Authorization` Header
```bash
curl -H "Authorization: Bearer YOUR_OPERATOR_API_KEY" \
     https://audioltdscrap-production.up.railway.app/api/v1/scraping/status
```

### Option C: Query Parameter `api_key` (Fast testing in browser/Postman)
```bash
curl "https://audioltdscrap-production.up.railway.app/api/v1/scraping/status?api_key=YOUR_OPERATOR_API_KEY"
```

### Authorizing in Swagger UI (`/docs`)
1. Open [`/docs`](https://audioltdscrap-production.up.railway.app/docs) in your browser.
2. Click the green **Authorize 🔓** button at the top right of the page.
3. In the **ApiKeyAuth** modal, paste your operator API key into the `Value` box.
4. Click **Authorize**, then click **Close**.
5. The lock icons will now show closed (🔒). Swagger will remember your key across sessions (`persistAuthorization: true`).

---

## 3. Standard Response Envelope & Error Codes

All API endpoints return JSON wrapped inside a uniform response envelope:

### Successful Response (HTTP 200 / 201)
```json
{
  "success": true,
  "message": "HTML snapshot saved and category/listing extracted successfully",
  "data": { ... },
  "meta": {
    "total": 36,
    "page": 1,
    "limit": 50
  }
}
```

### Standard Error Response
```json
{
  "detail": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing API key. Click Authorize in /docs and enter the operator API key."
  }
}
```

| HTTP Status | Error Code | Explanation / Action |
| :--- | :--- | :--- |
| **`401 Unauthorized`** | `UNAUTHORIZED` | API key was omitted or does not match server config. Click **Authorize** in `/docs`. |
| **`403 Forbidden`** | `ACCESS_RESTRICTED` | Target website Cloudflare challenge hit. Use snapshot file upload instead of live crawler. |
| **`404 Not Found`** | `NOT_FOUND` | The requested product, job, export, or category ID does not exist in the database. |
| **`422 Unprocessable`** | `PARSE_ERROR` / Validation | Malformed request body or unable to extract structured entities from the input. |
| **`502 Bad Gateway`** | `NETWORK_FETCH_ERROR` | Remote host unreachable or DNS/timeout failure. |

---

## 4. Five Practical End-to-End Workflows

### Workflow 1: Direct File Upload Scrape (Instant Snapshot Ingestion)
When Cloudflare restricts automated crawlers from datacenter IPs, use the file-upload endpoint:
1. Open the target category or product page in your regular desktop browser (e.g., Chrome).
2. Press `Ctrl + S` (or `Cmd + S`), choose **"Webpage, HTML Only"**, and save as `.html`.
3. Go to Swagger UI `/docs` -> **`POST /api/v1/scraping/upload-and-scrape`**.
4. Click **Try it out**, click **Choose File**, select your saved `.html` file, and click **Execute**.
5. The backend stores the snapshot in `data/raw/` and extracts all products, prices, images, subcategories, and pagination into PostgreSQL/SQLite immediately.

### Workflow 2: Starting an Automated Crawl Job
```bash
curl -X POST "https://audioltdscrap-production.up.railway.app/api/v1/scraping/start" \
     -H "X-API-Key: YOUR_OPERATOR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "mode": "category",
       "target_url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija",
       "max_depth": 3,
       "max_urls": 500,
       "download_delay": 2.0,
       "concurrency": 2
     }'
```
Response returns a `job_id`. Monitor progress via `GET /api/v1/jobs/{job_id}/progress`.

### Workflow 3: Searching and Filtering Extracted Products
Query the local database with filters, pagination, and sorting:
```bash
curl "https://audioltdscrap-production.up.railway.app/api/v1/products?brand=Bass%20Habit&min_price=50&max_price=300&page=1&limit=20"
```

### Workflow 4: Downloading Full CSV / JSON Exports
Generate a clean CSV spreadsheet with all extracted specifications:
```bash
# Direct stream download of all products in CSV format
curl -O -J "https://audioltdscrap-production.up.railway.app/api/v1/exports/products/csv"

# Or in JSON format
curl -O -J "https://audioltdscrap-production.up.railway.app/api/v1/exports/products/json"
```

### Workflow 5: Checking Catalog Coverage & Health
```bash
# Health check (No auth required)
curl "https://audioltdscrap-production.up.railway.app/api/v1/health"

# Detailed catalog overview report
curl -H "X-API-Key: YOUR_KEY" "https://audioltdscrap-production.up.railway.app/api/v1/reports/overview"
```

---

## 5. Complete API Reference by Module (All 70 Endpoints)

---

### Module 1: Scraping Control & Ingestion (`/api/v1/scraping`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/scraping/upload-and-scrape` | **Upload saved `.html` file** directly via multipart form. Extracts all products & saves raw snapshot. | **Yes** |
| `POST` | `/api/v1/scraping/snapshot-and-scrape` | Ingest raw HTML string via JSON payload or fetch live URL snapshot if accessible. | **Yes** |
| `GET` | `/api/v1/scraping/snapshots` | List all raw HTML files currently preserved on disk in `data/raw/`. | No |
| `POST` | `/api/v1/scraping/start` | Start an automated crawl job (`category`, `manufacturer`, `search`, `custom_urls`, `full`). | **Yes** |
| `POST` | `/api/v1/scraping/start/category` | Convenience launcher for category crawling. | **Yes** |
| `POST` | `/api/v1/scraping/start/manufacturer` | Convenience launcher for manufacturer/brand crawling. | **Yes** |
| `POST` | `/api/v1/scraping/start/search` | Convenience launcher for keyword search scraping. | **Yes** |
| `POST` | `/api/v1/scraping/start/urls` | Supply a batch of specific URLs to scrape. | **Yes** |
| `GET` | `/api/v1/scraping/status` | Current active crawl status, active workers, running jobs count. | No |
| `GET` | `/api/v1/scraping/history` | Historical log of executed scrape runs and outcomes. | No |
| `POST` | `/api/v1/scraping/pause/{job_id}` | Pause a running crawl job without losing frontier state. | **Yes** |
| `POST` | `/api/v1/scraping/resume/{job_id}` | Resume a paused crawl job. | **Yes** |
| `POST` | `/api/v1/scraping/cancel/{job_id}` | Stop and cancel a crawl job immediately. | **Yes** |
| `POST` | `/api/v1/scraping/ingest-html` | Raw HTML ingestion pipeline for background processing. | **Yes** |

---

### Module 2: Jobs & Crawl Frontier (`/api/v1/jobs` & `/api/v1/crawl`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/jobs` | List all crawl jobs with filter by status (`pending`, `running`, `completed`, `failed`). | No |
| `GET` | `/api/v1/jobs/{job_id}` | Detailed job information (seeds, parameters, timestamps, counters). | No |
| `GET` | `/api/v1/jobs/{job_id}/progress` | Real-time progress metrics (discovered, processed, failed, pages/sec). | No |
| `GET` | `/api/v1/jobs/{job_id}/results` | Paginated list of products extracted by this job. | No |
| `GET` | `/api/v1/jobs/{job_id}/errors` | List all error logs, HTTP 403 access restrictions, and timeouts for this job. | No |
| `GET` | `/api/v1/crawl/queue` | Inspect the pending URL frontier queue for a job. | No |
| `GET` | `/api/v1/crawl/failed` | View all URLs marked failed or retryable. | No |
| `POST` | `/api/v1/crawl/retry/{url_id}` | Re-queue a specific failed URL back to `queued`. | **Yes** |
| `POST` | `/api/v1/crawl/retry-failed` | Bulk re-queue all failed URLs for a job. | **Yes** |

---

### Module 3: Products Catalog (`/api/v1/products`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/products` | Query products with query parameters: `query`, `brand`, `min_price`, `max_price`, `in_stock`, `page`, `limit`. | No |
| `POST` | `/api/v1/products` | Manually insert a new product record. | **Yes** |
| `GET` | `/api/v1/products/{product_id}` | Fetch full product detail including specifications and images. | No |
| `PATCH` | `/api/v1/products/{product_id}` | Update product fields (e.g. price, stock, title). | **Yes** |
| `DELETE` | `/api/v1/products/{product_id}` | Delete a product record from the catalog. | **Yes** |
| `GET` | `/api/v1/products/sku/{sku}` | Lookup a product by its SKU identifier. | No |
| `GET` | `/api/v1/products/ean/{ean}` | Lookup a product by its EAN barcode. | No |
| `GET` | `/api/v1/products/{product_id}/specifications` | Get structured key-value specification attributes (RMS power, impedance, size, etc.). | No |
| `GET` | `/api/v1/products/{product_id}/categories` | List all categories this product belongs to. | No |
| `GET` | `/api/v1/products/{product_id}/sources` | Provenance records: source URL, crawl timestamp, HTTP response status. | No |
| `GET` | `/api/v1/products/{product_id}/translations` | Get English translations for this product. | No |

---

### Module 4: Categories & Navigation (`/api/v1/categories`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/categories` | List all discovered categories with parent-child links. | No |
| `GET` | `/api/v1/categories/tree` | Full nested hierarchical category tree (root categories down to leaves). | No |
| `GET` | `/api/v1/categories/coverage` | Category crawl coverage (% of catalog scraped per department). | No |
| `POST` | `/api/v1/categories/discover` | Scan the site's menu structure to register newly added categories. | **Yes** |
| `GET` | `/api/v1/categories/{category_id}` | Retrieve category metadata, description, and breadcrumbs. | No |
| `GET` | `/api/v1/categories/{category_id}/children` | Get direct child subcategories. | No |
| `GET` | `/api/v1/categories/{category_id}/products` | List all products assigned to this category. | No |

---

### Module 5: Manufacturers & Brands (`/api/v1/manufacturers`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/manufacturers` | List all audio manufacturers (Hertz, Audison, Bass Habit, Pioneer, etc.). | No |
| `GET` | `/api/v1/manufacturers/coverage` | Brand coverage report (product counts and completeness score per brand). | No |
| `POST` | `/api/v1/manufacturers/discover` | Discover manufacturers from brand directory page `/gamintojai`. | **Yes** |
| `GET` | `/api/v1/manufacturers/{manufacturer_id}` | Get manufacturer details and catalog URL. | No |
| `GET` | `/api/v1/manufacturers/{manufacturer_id}/products` | List all products manufactured by this brand. | No |

---

### Module 6: Search & Discovery (`/api/v1/search`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/search/products` | Full-text search across product titles, descriptions, and SKUs. | No |
| `GET` | `/api/v1/search/categories` | Search category titles and slugs. | No |
| `GET` | `/api/v1/search/manufacturers` | Search manufacturer brands. | No |
| `POST` | `/api/v1/search/scrape` | Trigger an on-demand scrape for a live search query on the target site. | **Yes** |

---

### Module 7: Exports & Downloads (`/api/v1/exports`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/exports/products/csv` | **Direct CSV download** of the product catalog. Compatible with Excel and Google Sheets. | No |
| `GET` | `/api/v1/exports/products/json` | **Direct JSON download** of all products with nested specifications. | No |
| `GET` | `/api/v1/exports/categories/json` | Export category hierarchy in JSON. | No |
| `GET` | `/api/v1/exports/jobs/{job_id}` | Download export containing only products scraped by a specific job. | No |
| `POST` | `/api/v1/exports/create` | Request an asynchronous background export file. | **Yes** |
| `GET` | `/api/v1/exports/{export_id}/status` | Check status of an asynchronous background export task. | No |
| `GET` | `/api/v1/exports/{export_id}/download` | Download generated export artifact once ready. | No |

---

### Module 8: Translations (`/api/v1/translations`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/translations/status` | Global translation engine status and pending translation queue. | No |
| `POST` | `/api/v1/translations/start` | Start batch translation for untranslated products. | **Yes** |
| `POST` | `/api/v1/translations/retry-failed` | Retry translation attempts that timed out or failed. | **Yes** |
| `GET` | `/api/v1/translations/products/{product_id}` | Retrieve English translation for a specific product. | No |
| `POST` | `/api/v1/translations/products/{product_id}` | Trigger immediate translation for a single product. | **Yes** |

---

### Module 9: Reports & Analytics (`/api/v1/reports`)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/reports/overview` | Executive telemetry: total products, total jobs, error rate, coverage %. | No |
| `GET` | `/api/v1/reports/coverage` | Detailed URL frontier breakdown (discovered vs processed vs restricted). | No |
| `GET` | `/api/v1/reports/completeness` | Data quality score (% of products with prices, EANs, specs, high-res images). | No |
| `GET` | `/api/v1/reports/errors` | Comprehensive error taxonomy (HTTP status codes, parser failures). | No |
| `GET` | `/api/v1/reports/categories` | Department-level catalog distribution and counts. | No |
| `GET` | `/api/v1/reports/manufacturers` | Brand-level catalog distribution and counts. | No |

---

### Module 10: Health, Readiness & System Stats (`/api/v1/system` & Top-Level)

| Method | Endpoint | Summary & Usage | Auth Required? |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Top-level system liveness check (Railway / Docker healthcheck). | No |
| `GET` | `/ready` | Database connectivity readiness check. | No |
| `GET` | `/api/v1/health` | API version and database connection health check. | No |
| `GET` | `/api/v1/health/ready` | Queue and storage readiness status. | No |
| `GET` | `/api/v1/system/status` | Server uptime, memory utilization, and active background threads. | No |
| `GET` | `/api/v1/system/stats` | Database row counts (products, categories, manufacturers, URLs). | No |

---

## 6. Code Examples (Python, JavaScript & cURL)

### Python (using `httpx` or `requests`)
```python
import httpx

BASE_URL = "https://audioltdscrap-production.up.railway.app"
API_KEY = "YOUR_OPERATOR_API_KEY"
headers = {"X-API-Key": API_KEY}

# 1. Upload a saved HTML file
with open("category_page.html", "rb") as f:
    files = {"file": ("category_page.html", f, "text/html")}
    data = {"url": "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija"}
    response = httpx.post(f"{BASE_URL}/api/v1/scraping/upload-and-scrape", headers=headers, data=data, files=files)
    print("Upload Result:", response.json())

# 2. Query products with price filter
products_resp = httpx.get(f"{BASE_URL}/api/v1/products", params={"min_price": 50, "max_price": 200, "limit": 10})
for prod in products_resp.json()["data"]:
    print(f"{prod['title']} — €{prod['price']}")
```

### JavaScript / TypeScript (`fetch`)
```javascript
const BASE_URL = "https://audioltdscrap-production.up.railway.app";
const API_KEY = "YOUR_OPERATOR_API_KEY";

// Fetch latest products
async function getProducts() {
  const response = await fetch(`${BASE_URL}/api/v1/products?limit=5`);
  const json = await response.json();
  console.log("Products:", json.data);
}

// Upload HTML file from an HTML <input type="file" id="fileInput">
async function uploadSnapshot(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("url", "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija");

  const response = await fetch(`${BASE_URL}/api/v1/scraping/upload-and-scrape`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
    },
    body: formData,
  });
  const result = await response.json();
  console.log("Scraped Items:", result.data.products);
}
```

---

## 7. Operational Best Practices & Troubleshooting

1. **Cloudflare Challenges on Live URLs**:
   - If an automated crawl logs `ACCESS_RESTRICTED` (HTTP 403), the site has triggered a Turnstile check.
   - Do not attempt to script bypasses.
   - Open the URL in your browser, press `Ctrl+S` ("Webpage, HTML Only"), and upload it via `POST /api/v1/scraping/upload-and-scrape`.

2. **Persistent Authorization**:
   - In `/docs`, your API key is preserved in `localStorage` across page reloads. If you open `/docs` on a new computer or private tab, simply click **Authorize** again.

3. **Data Integrity & Original Lithuanian Language**:
   - All product titles, descriptions, and category names are preserved in authentic Lithuanian source format.
   - When translations are requested via `/api/v1/translations`, translations are stored in a dedicated `product_translations` table, ensuring zero source data corruption.
