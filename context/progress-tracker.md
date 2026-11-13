# Progress Tracker

Update this file after every meaningful implementation or planning change. Record only verified progress. A new agent session must be able to resume by reading this file and the other context documents.

## Current Phase

- Phase 1 & 2: Context analysis and repository inspection completed.
- Phase 3: Live reconnaissance performed on `https://www.audiovideo.lt/`.
- Phase 4 - 15: Full application foundation, database models, durable frontier, extraction engines, complete REST API (`/api/v1/`), Jinja2 + HTMX operator dashboard, Docker / Railway setup, and Pytest test suite implemented inside `scraper/`.

## Current Goal

- Verification complete; all 20 automated tests passing across extraction, deduplication, URL frontier, API endpoints, and dashboard.

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

- **Job Execution & Scrapy / Celery Integration**:
  - `JobRunner` in `scraper/app/services/job_runner.py` for batch processing of claimed URLs.
  - Celery app and tasks in `scraper/app/tasks/` for background asynchronous processing.
  - Scrapy spider `AudiovideoSpider` and `DatabasePipeline` in `scraper/app/crawler/`.
  - Playwright fallback manager in `scraper/app/browser/playwright_manager.py`.

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

- **Automated Test Suite**:
  - 20 automated tests passing with Pytest covering extraction, deduplication, frontier lease mechanics, all API routers, and dashboard routes.

## In Progress

- Ready for review and deployment to Railway / production environment.

## Next Up

- Connect Railway PostgreSQL and Redis production connection strings.
- Run `alembic upgrade head` in Railway deployment pipeline.
- Start web service (`uvicorn app.main:app --host 0.0.0.0 --port 8000`) and worker (`celery -A app.tasks.celery_app worker -c 2`).

## Architecture Decisions

- Target-site access: Cloudflare challenge responses are categorized as `inaccessible` with error code `ACCESS_RESTRICTED`, maintaining strict adherence to anti-bot and security policies.
- Database: SQLite default fallback for zero-dependency local testing/dev, PostgreSQL for Docker and Railway deployments.
- API structure: Modular routers versioned under `/api/v1/` with consistent JSON envelope schemas (`APIResponse[T]`, `PaginationMeta`, `APIErrorResponse`).
