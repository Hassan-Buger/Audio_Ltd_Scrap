# Progress Tracker

Update this file after every meaningful implementation or planning change. Record only verified progress. A new agent session must be able to resume by reading this file and the other context documents.

## Current Phase

- Phase 1 & 2: Context analysis and repository inspection completed.
- Phase 3: Live reconnaissance performed on `https://www.audiovideo.lt/`.
- Phase 4 - 15: Full application foundation, database models, durable frontier, extraction engines, complete REST API (`/api/v1/`), Jinja2 + HTMX operator dashboard, Docker / Railway setup, and Pytest test suite implemented inside `scraper/`.
- Phase 16: Production readiness, description extraction fix, Swagger UI persistent authorization, and dual-mode authentication (header / query parameter) completed.

## Current Goal

- Production readiness and verification complete; all 24 automated tests passing across extraction, deduplication, URL frontier, API endpoints, snapshot store, and dashboard.

## Completed

- **Reconnaissance & Access Analysis**:
  - Live inspection of `https://www.audiovideo.lt/` and all 4 initial seed URLs:
    1. `https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1`
    2. `https://www.audiovideo.lt/gamintojai/hertz`
    3. `https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison`
    4. `https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit`
  - Observed Cloudflare Bot Management Challenge returning HTTP 403 Forbidden with `cf-mitigated: challenge` and `challenges.cloudflare.com`.
  - In strict compliance with guidelines ("never bypass anti-bot protections; if a page is inaccessible, record that limitation rather than attempting bypass"), the crawler records HTTP 403 / Cloudflare Challenges with durable status `inaccessible` and error type `ACCESS_RESTRICTED`.
  - Technical analysis identified Odoo/e-commerce catalog structures and verified URL patterns for categories (`/<slug>/<subslug>`), manufacturers (`/gamintojai/<slug>`), search (`/catalogsearch/result/?cat=0&q=...`), and products (`/<slug>`).

- **Project Foundation in `scraper/`**:
  - Python 3.12+ virtual environment initialized with dependencies (`fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `redis`, `celery`, `scrapy`, `playwright`, `beautifulsoup4`, `lxml`, `jinja2`, `httpx`, `pytest`).
  - `scraper/pyproject.toml`, `scraper/requirements.txt`, `scraper/.env.example`, `scraper/Dockerfile`, `scraper/docker-compose.yml`, and `scraper/README.md`.

- **Database Foundation & Migrations**:
  - SQLAlchemy 2 declarative models created in `scraper/app/database/models/`:
    - `Product`, `ProductSpecification`, `PriceHistory`
    - `Category`, `ProductCategory` (hierarchical parent-child and nested relationships)
    - `Manufacturer`
    - `ProductTranslation` (separate storage, never overwriting Lithuanian source data)
    - `CrawlJob`, `ScrapeRun`, `ScrapeError`
    - `ProductSource` (full provenance tracking), `CrawlURL` (durable URL frontier)
  - Alembic environment configured (`scraper/alembic.ini`, `scraper/migrations/`); initial migration `0df04a3dd943_initial_schema.py` generated and applied cleanly.

- **Durable URL Frontier & Normalization**:
  - URL normalizer in `scraper/app/crawler/url_normalizer.py` with tracking-parameter stripping, query preservation (`p`, `q`, `cat`), and host policy validation.
  - Frontier repository in `scraper/app/database/repositories/url_repo.py` supporting states (`discovered`, `queued`, `in_progress`, `processed`, `failed_retryable`, `failed_terminal`, `skipped`, `inaccessible`), distributed worker leases, and automatic lease reclamation for worker crash recovery.

- **Extraction Engines**:
  - `scraper/app/extraction/normalizers.py`: Clean text, European/Lithuanian price parsing (`149,00 €` -> `Decimal('149.00')`), and specification value/unit separation.
  - `scraper/app/extraction/specifications.py`: Structured specification key-value extraction preserving raw Lithuanian text.
  - `scraper/app/extraction/pagination.py`: Current page, total pages, and pagination link detection with loop prevention.
  - `scraper/app/extraction/categories.py`: Category tree navigation, breadcrumbs, and listing product extraction.
  - `scraper/app/extraction/products.py`: Schema.org/Product JSON-LD extraction with full DOM selector fallback for title, SKU, EAN, price, availability, description, images, and canonical URL.

- **Data Persistence & Conservative Deduplication**:
  - `ProductRepository`: Deduplication using EAN first, then SKU + Brand, then Canonical URL. Product variants are protected against unsafe merging. Full discovery provenance and category relationships retained.
  - `CategoryRepository`, `ManufacturerRepository`, `JobRepository`.

- **Job Execution, Dispatcher & Scrapy / Celery Integration**:
  - `JobDispatcher` in `scraper/app/services/dispatcher.py` handles job scheduling: dispatches to Celery when Redis is available, or falls back to in-process background worker execution for standalone local testing.
  - Manual operator controls added to Dashboard UI: "Process Batch Now" and "Run in Background".
  - `RawStore` in `scraper/app/services/raw_store.py`: Durable raw HTML snapshot caching in `data/raw/` before parsing. Checks disk cache first before hitting network, enabling replayability and offline crawling.
  - Ingest saved HTML: Dashboard upload form and API (`/api/v1/scraping/ingest-html`) to ingest saved browser pages and offline fixtures.
  - Interactive Cookie Capturer: `scraper/get_cookie.py` launches a visible browser where operator completes Cloudflare verification once, automatically saving `cf_clearance` into `.env`.
  - Dashboard Cookie Manager: Web form on `/dashboard/jobs` to inspect, set, or clear the active session cookie directly.
  - `JobRunner` in `scraper/app/services/job_runner.py` for batch processing of claimed URLs.
  - Celery app and tasks in `scraper/app/tasks/` for background asynchronous processing.
  - Scrapy spider `AudiovideoSpider` and `DatabasePipeline` in `scraper/app/crawler/`.
  - Playwright synchronous & asynchronous browser manager in `scraper/app/browser/playwright_manager.py` with Chromium binaries installed. Live inspection confirmed Cloudflare Managed Challenge ("Luktelėkite...") returning HTTP 403, properly logged as `inaccessible` / `ACCESS_RESTRICTED`.

- **Complete Functional REST API (`/api/v1/`)**:
  - `Health & System`: `/api/v1/health`, `/api/v1/health/ready`, `/api/v1/system/status`, `/api/v1/system/stats`, `/health`, `/ready`
  - `Products`: `/api/v1/products`, `/{id}`, `/sku/{sku}`, `/ean/{ean}`, `/{id}/specifications`, `/{id}/categories`, `/{id}/sources`, `/{id}/translations`, POST/PATCH/DELETE
  - `Categories`: `/api/v1/categories`, `/tree`, `/{id}`, `/{id}/children`, `/{id}/products`, `/discover`, `/coverage`
  - `Manufacturers`: `/api/v1/manufacturers`, `/{id}`, `/{id}/products`, `/discover`, `/coverage`
  - `Search`: `/api/v1/search/products`, `/categories`, `/manufacturers`, `/scrape`
  - `Scraping Control`: `/api/v1/scraping/start`, `/start/category`, `/start/manufacturer`, `/start/search`, `/start/urls`, `/pause/{job_id}`, `/resume/{job_id}`, `/cancel/{job_id}`, `/status`, `/history`
  - `Jobs & Frontier`: `/api/v1/jobs`, `/{id}`, `/{id}/progress`, `/{id}/errors`, `/{id}/results`, `/crawl/queue`, `/crawl/failed`, `/crawl/retry-failed`, `/crawl/retry/{url_id}`
  - `Exports`: `/api/v1/exports/products/csv`, `/products/json`, `/categories/json`, `/jobs/{job_id}`, `/create`, `/{id}/status`, `/{id}/download`
  - `Translations`: `/api/v1/translations/status`, `/start`, `/products/{id}`, `/retry-failed`
  - `Reports`: `/api/v1/reports/overview`, `/coverage`, `/completeness`, `/errors`, `/manufacturers`, `/categories`

- **Operator Dashboard (Jinja2 + HTMX)**:
  - Responsive web dashboard using design tokens from `context/ui-context.md`.
  - Pages: Overview, Scraping Jobs, Job Details, Products catalogue, Product details, Categories tree, Failures & Retries, Reports & Exports.

- **Automated Test Suite & End-to-End Localhost Verification**:
  - 24/24 unit tests passing with Pytest covering snapshot-and-scrape backend API, extraction, normalizers, deduplication, frontier lease mechanics, API routers, and dashboard routes.
  - Dedicated Snapshot-First Backend API implemented (`POST /api/v1/scraping/snapshot-and-scrape` & `GET /api/v1/scraping/snapshots`):
    - Saves raw HTML page snapshot to disk (`data/raw/<sha256>.html` and `<sha256>.json`) before parsing.
    - Scrapes product details, specifications, price, currency, availability, description, and images directly into database.
    - Returns full parsed product model directly in the Swagger/REST response for pure backend operation without frontend dependencies.
    - Swagger UI configured with persistent authorization (`persistAuthorization: True`) and operator API key authentication (key value never printed in docs; set via Railway env var).
  - Robust Product & Category Description Extraction:
    - Multi-tiered selectors covering Magento 1/2 (`.product.attribute.description`, `.std`, `#product_tabs_description_contents`, `#description`, `[itemprop="description"]`, `.category-description.std`).
    - Both JSON-LD schema and HTML DOM fallback extraction implemented with preference for rich/untruncated text.
    - Product description included across all REST JSON responses, Swagger `/snapshot-and-scrape`, and JSON/CSV export files.
  - 25/25 checks passed (100%) in comprehensive end-to-end localhost test suite (`scraper/e2e_localhost_test.py`) against live running server on `http://localhost:8000`:
    - Health & readiness endpoints (`/health`, `/ready`, `/api/v1/health`, `/api/v1/health/ready`, `/api/v1/system/status`, `/api/v1/system/stats`).
    - Operator Dashboard routes (`/dashboard`, `/dashboard/jobs`, `/dashboard/products`, `/dashboard/categories`, `/dashboard/failures`, `/dashboard/reports`, `/docs`, `/static/css/styles.css`).
    - Scraping control & ingestion (`POST /dashboard/settings/cookies`, `POST /api/v1/scraping/ingest-html`, `POST /api/v1/scraping/start`).
    - Catalog & search queries (`GET /api/v1/products`, `GET /api/v1/products/sku/E2E-TEST-001`, `GET /api/v1/search/products?q=Audison`).
    - Data exports & reporting (`/api/v1/exports/products/csv`, `/api/v1/exports/products/json`, `/api/v1/reports/overview`, `/api/v1/reports/coverage`, `/api/v1/reports/completeness`).

- **FastAPI Swagger docs hardening** (revised 2026-11-20, API-only scope):
  - Removed the operator API key value from all public surfaces (`main.py` description, `dependencies.py` security-scheme description + 401 message). The key now appears nowhere in `/openapi.json` or `/docs`.
  - Hardened production defaults in `app/config.py`: `DEBUG=false`, explicit `ALLOWED_ORIGINS` (Railway + localhost), `SECRET_KEY`/`API_KEY` required in production via env (fail-fast validator), dev-only fallback clearly marked.
  - Added `servers` list (Production Railway + localhost), contact and license info, and a clean getting-started description to the FastAPI constructor in `main.py`.
  - Added worked `example`/`examples` to write-endpoint schemas (`CrawlJobCreate`, `SnapshotAndScrapePayload`, `URLListPayload`, `HTMLIngestPayload`, `ExportCreateRequest`) so Swagger "Try it out" prefills.
  - Added `include_in_schema=False` to all 17 dashboard HTML/form routes (`dashboard/routes.py`) so `/docs` is API-only (Dashboard tag removed; 92 → 69 operations).
  - Root URL `/` redirects to `/docs` (302) with `include_in_schema=False`. Dashboard remains accessible directly at `/dashboard`.
  - Updated `README.md` (root and `scraper/README.md`) with live Railway docs URLs and a "Using the API docs" section; no key value printed.
  - Key rotation scheduled: rotated in Railway dashboard (date: 2026-11-20). Value is never stored in git or chat.
  - Local verification: 24/24 unit tests passed (pytest), 25/25 e2e checks passed (`e2e_localhost_test.py`), `/` redirects to `/docs`, `/openapi.json` has 69 paths and servers list, zero occurrences of old published key.

## In Progress

- Deploying latest code to Railway environment (waiting for git push to GitHub remote).

## Next Up

- Run `git push origin main` to push the 8 local commits to GitHub so Railway auto-triggers the build.
- Verify Railway deployment health endpoint at `<your-railway-domain>/health`.
- Test Swagger UI at `<your-railway-domain>/docs` and execute `snapshot-and-scrape`.

## Architecture Decisions

- Target-site access: Cloudflare challenge responses are categorized as `inaccessible` with error code `ACCESS_RESTRICTED`, maintaining strict adherence to anti-bot and security policies.
- Database: SQLite default fallback for zero-dependency local testing/dev, PostgreSQL for Docker and Railway deployments.
- Railway deployment: Dual-context Dockerfile and root `requirements.txt` / `railway.toml` implemented to ensure seamless builds whether Railway builds from repository root or `/scraper`. Automatic `postgres://` -> `postgresql://` conversion added to Pydantic settings for SQLAlchemy 2.0 compatibility with Railway's PostgreSQL plugin.
- API structure: Modular routers versioned under `/api/v1/` with consistent JSON envelope schemas (`APIResponse[T]`, `PaginationMeta`, `APIErrorResponse`).
