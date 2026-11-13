# Audiovideo.lt Product Scraper & Operations Console

Production-grade, modular Python application for discovering, extracting, deduplicating, and monitoring product catalogue data from [audiovideo.lt](https://www.audiovideo.lt/).

## Key Features

- **Robust Web Crawling**: Scrapy-based asynchronous fetching with configurable rate-limiting, politeness delays, bounded depth, and host whitelisting. Controlled Playwright fallback for pages requiring browser rendering.
- **Durable URL Frontier**: PostgreSQL-backed frontier with states: `discovered`, `queued`, `in_progress`, `processed`, `failed_retryable`, `failed_terminal`, `skipped`, and `inaccessible`. Supports lease recovery, worker crash tolerance, and bounded backoff.
- **Lithuanian Source Preservation**: Original Lithuanian titles, descriptions, and technical specifications are preserved intact. English translations are stored separately and are optional/independently retryable.
- **Conservative Identity & Deduplication**: Distinct product variants are protected; products discovered via multiple paths (category, nested subcategories, manufacturer, search) are linked without data loss.
- **Full REST API (v1)**: FastAPI implementation covering health, products, categories, manufacturers, search, scraping jobs, exports (CSV/JSON), translations, and audit reports.
- **Operator Dashboard**: Server-rendered Jinja2 + HTMX console for monitoring jobs, inspecting extraction completeness, browsing the category tree, and triggering retries.
- **Railway & Docker Ready**: Containerized architecture with decoupled web and Celery worker services.

## Architecture

- **Backend**: FastAPI (Python 3.12+)
- **Crawler**: Scrapy with persistent PostgreSQL frontier adapter
- **Browser Fallback**: Playwright
- **Database & ORM**: PostgreSQL with SQLAlchemy 2 and Alembic migrations
- **Queue/Broker**: Redis & Celery
- **Dashboard**: Jinja2 templates, HTMX, and CSS design tokens

## Setup & Running

### 1. Environment Setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

### 2. Database Migrations
```bash
alembic upgrade head
```

### 3. Run Web Service & Dashboard
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to:
- Dashboard: `http://localhost:8000/dashboard`
- Swagger API Docs: `http://localhost:8000/docs`
- ReDoc API Docs: `http://localhost:8000/redoc`

### 4. Run Celery Worker
```bash
celery -A app.tasks.celery_app worker --loglevel=info -c 2
```

### 5. Run Automated Tests
```bash
pytest
```
