"""Category tree extraction, breadcrumb navigation, and listing URLs."""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.schemas.category import CategoryCreate
from .normalizers import clean_text, parse_price


def extract_breadcrumbs(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """Extract breadcrumb navigation links and titles."""
    crumbs = []
    # Common breadcrumbs: .breadcrumbs, nav[aria-label="breadcrumb"], ol.breadcrumb
    container = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["breadcrumb", "crumbs"]))
    if not container:
        container = soup.find("nav", attrs={"aria-label": lambda a: a and "breadcrumb" in a.lower()})

    if container:
        items = container.find_all(["li", "span", "a"])
        for item in items:
            a = item.find("a") if item.name != "a" else item
            text = clean_text(item.get_text())
            href = a["href"].strip() if (a and a.has_attr("href")) else None
            full_url = urljoin(base_url, href) if href else None
            if text and text not in (">", "/", "»"):
                crumbs.append({"name": text, "url": full_url})
    return crumbs


def extract_category_tree(soup: BeautifulSoup, base_url: str) -> List[CategoryCreate]:
    """
    Extract category and subcategory links from navigation menus or sidebars.
    """
    categories: List[CategoryCreate] = []
    seen_urls = set()

    # Look for category navigation menus: nav, .navigation, .nav-sections, #nar-categories, .block-category-list
    navs = soup.find_all(["nav", "div", "ul"], class_=lambda c: c and any(k in str(c).lower() for k in ["category", "nav-main", "menu", "kategorij"]))
    
    for nav in navs:
        # Find all category links
        for a in nav.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "tel:", "mailto:")):
                continue
            
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            # Must be same host and non-empty path
            if not parsed.path or parsed.path == "/":
                continue
            
            # Exclude account/cart/checkout
            if any(x in parsed.path for x in ["customer", "checkout", "cart", "contact", "about"]):
                continue

            slug = parsed.path.strip("/")
            name = clean_text(a.get_text())

            if name and full_url not in seen_urls and len(name) > 1:
                seen_urls.add(full_url)
                level = slug.count("/")
                categories.append(CategoryCreate(
                    name=name,
                    slug=slug,
                    source_url=full_url,
                    level=level,
                    is_leaf=False
                ))

    return categories


def extract_listing_products(soup: BeautifulSoup, base_url: str) -> List[str]:
    """
    Extract product detail URLs from a category, manufacturer, or search listing page.
    """
    product_urls: List[str] = []
    seen = set()

    # Search for product card containers: .product-item, .item, .product-card, etc.
    cards = soup.find_all(class_=lambda c: c and any(k in str(c).lower() for k in ["product-item", "product-card", "product-box", "item-product"]))
    if not cards:
        # Try generic article or li with product links
        cards = soup.find_all(["article", "li"], class_=lambda c: c and "product" in str(c).lower())

    for card in cards:
        a = card.find("a", class_=lambda c: c and any(k in str(c).lower() for k in ["product-item-link", "title", "name", "thumb"]))
        if not a:
            a = card.find("a", href=True)
        if a and a.has_attr("href"):
            full = urljoin(base_url, a["href"].strip())
            if full not in seen:
                seen.add(full)
                product_urls.append(full)

    # Fallback if no cards found: inspect any link that resembles an Audiovideo.lt product detail page
    if not product_urls:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            path = parsed.path.strip("/")
            # Audiovideo.lt products have slugs with model numbers or dashes
            if path and (path.count("-") >= 3 or any(c.isdigit() for c in path)):
                if not any(x in path for x in ["customer", "cart", "checkout", "catalogsearch", "gamintojai"]):
                    if full not in seen:
                        seen.add(full)
                        product_urls.append(full)

    return product_urls


def extract_category_description(soup: BeautifulSoup) -> Optional[str]:
    """Extract category description text from category listing page."""
    selectors = [
        ".category-description.std",
        ".category-description",
        "#category-description",
        '[itemprop="description"]',
        ".category-view .std",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            txt = clean_text(el.get_text())
            if txt and len(txt) >= 5:
                return txt

    meta_el = soup.select_one('meta[name="description"]') or soup.select_one('meta[property="og:description"]')
    if meta_el and meta_el.get("content"):
        txt = clean_text(meta_el["content"])
        if txt and len(txt) >= 5:
            return txt

    return None


def extract_listing_product_items(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """
    Extract structured product cards (title, url, price, image) directly from category listing.
    """
    items: List[Dict[str, Any]] = []
    seen = set()

    cards = soup.select(".products-grid .item, .category-products-grid .item, .products-list .item, .product-item, .item-product")
    if not cards:
        cards = soup.find_all(class_=lambda c: c and any(k in str(c).lower() for k in ["product-item", "product-card", "item"]))

    for card in cards:
        a = card.select_one(".product-name a, .product-item-link, a.title, h2 a, h3 a")
        if not a:
            a = card.find("a", href=True)
        if not a or not a.has_attr("href"):
            continue

        full_url = urljoin(base_url, a["href"].strip())
        if full_url in seen:
            continue
        seen.add(full_url)

        title = clean_text(a.get_text()) or a.get("title") or ""
        if not title:
            continue

        price_el = card.select_one(".price-box .price, .special-price .price, .regular-price .price, .price")
        price_val, currency = parse_price(price_el.get_text()) if price_el else (None, "EUR")

        img_el = card.find("img")
        img_url = None
        if img_el:
            src = img_el.get("src") or img_el.get("data-src")
            if src and not src.startswith("data:"):
                img_url = urljoin(base_url, src.strip())

        items.append({
            "title": title,
            "url": full_url,
            "price": float(price_val) if price_val is not None else None,
            "currency": currency,
            "image": img_url
        })

    return items
