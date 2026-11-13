"""URL normalization, host policy validation, and URL type classification."""
import re
from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from app.config import settings
from app.schemas.crawl import URLType

# Query parameters to preserve for Audiovideo.lt
PRESERVED_PARAMS = {"p", "q", "cat", "dir", "order", "limit"}

# Tracking / disposable parameters to strip
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "_ga", "_gl", "mc_cid", "mc_eid"
}


def is_allowed_host(url: str) -> bool:
    """Validate that the URL belongs to an allowed host and uses http(s)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.netloc.lower().split(":")[0]
    return host in settings.TARGET_ALLOWED_HOSTS


def normalize_url(url: str) -> str:
    """Normalize a URL to prevent duplicate scheduling while preserving meaningful parameters."""
    if not url:
        return ""
    
    parsed = urlparse(url.strip())
    scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme
    netloc = parsed.netloc.lower()
    
    # Path normalization: strip trailing slash except for root
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
        
    # Clean query parameters
    query_tuples = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            k_lower = k.lower()
            if k_lower not in TRACKING_PARAMS:
                query_tuples.append((k_lower, v))
        query_tuples.sort()
        
    cleaned_query = urlencode(query_tuples)
    
    # Drop fragments
    return urlunparse((scheme, netloc, path, "", cleaned_query, ""))


def classify_url(url: str) -> URLType:
    """Classify an Audiovideo.lt URL into its structural category."""
    parsed = urlparse(url)
    path = parsed.path.lower().strip("/")
    query = dict(parse_qsl(parsed.query))

    if not path and not query:
        return URLType.UNKNOWN

    # Search result pages
    if "catalogsearch" in path or ("q" in query and query.get("q")):
        return URLType.SEARCH

    # Manufacturer / brand listing pages
    if path.startswith("gamintojai") or "gamintojai" in path:
        return URLType.MANUFACTURER

    # Pagination pages
    if "p" in query and query["p"].isdigit():
        return URLType.PAGINATION

    # Multi-segment paths typically represent category or subcategory
    segments = [s for s in path.split("/") if s]
    if len(segments) > 1:
        # If last segment ends with an obvious product extension or slug
        # On audiovideo.lt, categories have slugs like 'automobiliu-garso-aparatura/garso-izoliacija'
        return URLType.CATEGORY

    if len(segments) == 1:
        # Single segment can be a root category or a product URL
        # For instance: 'garso-aparatura' vs 'hertz-ml-700-set-midrange'
        slug = segments[0]
        # Products usually contain model numbers, multiple dashes, or brand names
        if any(char.isdigit() for char in slug) or slug.count("-") >= 3:
            return URLType.PRODUCT
        return URLType.CATEGORY

    return URLType.UNKNOWN
