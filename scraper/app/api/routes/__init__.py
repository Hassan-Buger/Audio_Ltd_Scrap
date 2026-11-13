"""API Routes package."""
from .health import router as health_router
from .products import router as products_router
from .categories import router as categories_router
from .manufacturers import router as manufacturers_router
from .search import router as search_router
from .scraping import router as scraping_router
from .jobs import router as jobs_router
from .exports import router as exports_router
from .translations import router as translations_router
from .reports import router as reports_router

__all__ = [
    "health_router",
    "products_router",
    "categories_router",
    "manufacturers_router",
    "search_router",
    "scraping_router",
    "jobs_router",
    "exports_router",
    "translations_router",
    "reports_router",
]
