"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import init_db
from app.api.routes import (
    health_router,
    products_router,
    categories_router,
    manufacturers_router,
    search_router,
    scraping_router,
    jobs_router,
    exports_router,
    translations_router,
    reports_router,
)
from app.dashboard.routes import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="Audiovideo.lt Product Scraper & Operations API",
    description="""
### Audiovideo.lt Product Scraper & Operations API

Operates the Audiovideo.lt product catalogue scraper: crawl jobs, product/category/manufacturer
listings, search, CSV/JSON exports, translations, and coverage reports.

Quick start:
1. Open `/docs`.
2. Try `GET /api/v1/health` (no authentication required).
3. Click **Authorize** and paste the operator API key (from your Railway environment variables
   or the operator runbook).
4. Try `POST /api/v1/scraping/start` to create a crawl job.

All responses use the envelope `{ success, message, data, meta? }`.
See `/redoc` for the readable API reference.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
    servers=[
        {"url": "https://audioltdscrap-production.up.railway.app", "description": "Production (Railway)"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ],
    contact={"name": "Audiovideo.lt Scraper Operator"},
    license_info={"name": "Proprietary — internal use"},
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for dashboard
static_dir = os.path.join(os.path.dirname(__file__), "dashboard", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount API Routers under /api/v1
API_V1_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(products_router, prefix=API_V1_PREFIX)
app.include_router(categories_router, prefix=API_V1_PREFIX)
app.include_router(manufacturers_router, prefix=API_V1_PREFIX)
app.include_router(search_router, prefix=API_V1_PREFIX)
app.include_router(scraping_router, prefix=API_V1_PREFIX)
app.include_router(jobs_router, prefix=API_V1_PREFIX)
app.include_router(exports_router, prefix=API_V1_PREFIX)
app.include_router(translations_router, prefix=API_V1_PREFIX)
app.include_router(reports_router, prefix=API_V1_PREFIX)

# Top-level Health and Readiness endpoints (per architecture.md)
@app.get("/health", tags=["Health & System"])
def root_health():
    return {"status": "ok", "service": "audiovideo-scraper"}


@app.get("/ready", tags=["Health & System"])
def root_ready():
    return {"status": "ready", "database": "connected"}


# Web Dashboard
app.include_router(dashboard_router)


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs", status_code=status.HTTP_302_FOUND)


# Global Exception Handler for consistent error envelope
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Only return JSON error envelope for /api routes
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An internal server error occurred",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "details": {"error": str(exc) if settings.DEBUG else None}
                }
            }
        )
    raise exc
