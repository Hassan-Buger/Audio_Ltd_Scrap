"""Product detail page extraction engine supporting JSON-LD and HTML parsing."""
import json
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from app.schemas.product import ProductCreate, SpecificationItem
from .normalizers import clean_text, parse_price
from .specifications import extract_specifications


def extract_product_detail(html_content: str, source_url: str) -> Optional[ProductCreate]:
    """
    Extract full product detail from raw HTML.
    Supports JSON-LD parsing with robust DOM fallback.
    """
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, "lxml")

    # 1. Try JSON-LD first
    product_data = _extract_from_json_ld(soup, source_url)

    # 2. Extract or fill missing fields from HTML DOM
    dom_title = _extract_title(soup)
    dom_sku = _extract_sku(soup)
    dom_ean = _extract_ean(soup)
    dom_model = _extract_model(soup)
    dom_brand = _extract_brand(soup)
    dom_price, dom_regular_price, dom_currency = _extract_prices(soup)
    dom_availability, dom_in_stock = _extract_availability(soup)
    dom_description = _extract_description(soup)
    dom_images = _extract_images(soup, source_url)
    dom_canonical = _extract_canonical_url(soup, source_url)
    dom_specs = extract_specifications(soup)

    title = (product_data.get("title") if product_data else None) or dom_title or ""
    if not title:
        return None

    sku = (product_data.get("sku") if product_data else None) or dom_sku
    ean = (product_data.get("ean") if product_data else None) or dom_ean
    model = (product_data.get("model") if product_data else None) or dom_model
    brand_name = (product_data.get("brand_name") if product_data else None) or dom_brand
    
    price = (product_data.get("price") if product_data else None) or dom_price
    regular_price = (product_data.get("regular_price") if product_data else None) or dom_regular_price
    currency = (product_data.get("currency") if product_data else None) or dom_currency or "EUR"
    
    availability = (product_data.get("availability") if product_data else None) or dom_availability
    in_stock = (product_data.get("in_stock") if product_data else None)
    if in_stock is None:
        in_stock = dom_in_stock
        
    description = (product_data.get("description") if product_data else None) or dom_description
    images = (product_data.get("images") if product_data else None) or dom_images or []
    canonical_url = (product_data.get("canonical_url") if product_data else None) or dom_canonical or source_url
    
    specs = dom_specs
    if product_data and product_data.get("specifications"):
        specs.extend(product_data["specifications"])

    is_complete = bool(title and price is not None and (sku or canonical_url))

    return ProductCreate(
        canonical_url=canonical_url,
        title=title,
        sku=sku,
        ean=ean,
        model=model,
        brand_name=brand_name,
        price=price,
        regular_price=regular_price,
        currency=currency,
        availability=availability,
        in_stock=in_stock,
        description=description,
        images=images,
        is_complete=is_complete,
        specifications=specs,
        source_url=source_url,
        discovery_type="direct"
    )


def _extract_from_json_ld(soup: BeautifulSoup, source_url: str) -> Optional[Dict[str, Any]]:
    """Extract schema.org/Product structured data if present."""
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string or script.get_text() or "{}")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in ("Product", "IndividualProduct"):
                    offers = item.get("offers", {})
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    
                    price_val = None
                    currency = "EUR"
                    availability = None
                    in_stock = None
                    if isinstance(offers, dict):
                        raw_p = offers.get("price")
                        if raw_p is not None:
                            price_val, currency = parse_price(str(raw_p))
                        availability = offers.get("availability")
                        if availability:
                            if "InStock" in availability:
                                in_stock = True
                            elif "OutOfStock" in availability:
                                in_stock = False
                    
                    brand = item.get("brand")
                    brand_name = brand.get("name") if isinstance(brand, dict) else str(brand) if brand else None
                    
                    images = item.get("image", [])
                    if isinstance(images, str):
                        images = [images]

                    return {
                        "title": clean_text(item.get("name")),
                        "sku": clean_text(item.get("sku")),
                        "ean": clean_text(item.get("gtin13") or item.get("gtin8") or item.get("gtin")),
                        "model": clean_text(item.get("model")),
                        "brand_name": clean_text(brand_name),
                        "price": price_val,
                        "currency": currency,
                        "availability": availability,
                        "in_stock": in_stock,
                        "description": clean_text(item.get("description")),
                        "images": [urljoin(source_url, img) for img in images if img],
                        "canonical_url": item.get("url")
                    }
        except Exception:
            continue
    return None


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    # Typical product titles: h1.page-title, h1[itemprop="name"], h1.product-title, h1
    h1 = soup.find("h1", class_=lambda c: c and any(k in str(c).lower() for k in ["title", "name", "product"]))
    if not h1:
        h1 = soup.find("h1")
    return clean_text(h1.get_text()) if h1 else None


def _extract_sku(soup: BeautifulSoup) -> Optional[str]:
    # Look for [itemprop="sku"], .sku, or text matching Prekės kodas / Kodas
    sku_el = soup.find(attrs={"itemprop": "sku"})
    if not sku_el:
        sku_el = soup.find(class_=lambda c: c and "sku" in str(c).lower())
    if sku_el:
        val = clean_text(sku_el.get_text())
        if val:
            # Strip prefixes like 'Kodas:', 'Prekės kodas:'
            return re.sub(r"^(?:Prekės\s*kodas|Kodas|SKU)\s*[:.]?\s*", "", val, flags=re.IGNORECASE).strip()

    # Search in text nodes
    for text in soup.find_all(string=re.compile(r"(?:Prekės\s*kodas|Kodas|SKU)\s*:", re.IGNORECASE)):
        parent = text.parent
        full_text = clean_text(parent.get_text())
        if full_text:
            match = re.search(r"(?:Prekės\s*kodas|Kodas|SKU)\s*:\s*([A-Za-z0-9_-]+)", full_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return None


def _extract_ean(soup: BeautifulSoup) -> Optional[str]:
    # Look for [itemprop="gtin13"], [itemprop="gtin"], or EAN labels
    ean_el = soup.find(attrs={"itemprop": lambda a: a and "gtin" in str(a).lower()})
    if ean_el:
        return clean_text(ean_el.get_text())
    
    for text in soup.find_all(string=re.compile(r"(?:EAN|Barkodas)\s*:", re.IGNORECASE)):
        parent = text.parent
        full_text = clean_text(parent.get_text())
        if full_text:
            match = re.search(r"(?:EAN|Barkodas)\s*:\s*(\d{8,14})", full_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return None


def _extract_model(soup: BeautifulSoup) -> Optional[str]:
    model_el = soup.find(attrs={"itemprop": "model"})
    if model_el:
        return clean_text(model_el.get_text())
    return None


def _extract_brand(soup: BeautifulSoup) -> Optional[str]:
    brand_el = soup.find(attrs={"itemprop": "brand"})
    if not brand_el:
        brand_el = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["brand", "gamintoj", "manufacturer"]))
    if brand_el:
        val = clean_text(brand_el.get_text())
        if val:
            return re.sub(r"^(?:Gamintojas|Prekės\s*ženklas|Brand)\s*[:.]?\s*", "", val, flags=re.IGNORECASE).strip()
    return None


def _extract_prices(soup: BeautifulSoup) -> tuple:
    price_val = None
    regular_val = None
    currency = "EUR"

    # Price container: .price, [itemprop="price"], .final-price, .special-price, .regular-price
    special = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["special-price", "current-price", "now-price"]))
    if special:
        price_val, currency = parse_price(special.get_text())
        old = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["old-price", "regular-price", "was-price"]))
        if old:
            regular_val, _ = parse_price(old.get_text())
    else:
        # Standard price
        price_el = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["price-wrapper", "final-price", "product-price", "price"]))
        if price_el:
            price_val, currency = parse_price(price_el.get_text())

    return price_val, regular_val, currency


def _extract_availability(soup: BeautifulSoup) -> tuple:
    avail_el = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["availability", "stock", "likutis", "sandelyje"]))
    if avail_el:
        txt = clean_text(avail_el.get_text())
        in_stock = None
        if txt:
            lower = txt.lower()
            if any(k in lower for k in ["yra", "sandėlyje", "in stock", "turime"]):
                in_stock = True
            elif any(k in lower for k in ["nėra", "išparduota", "out of stock", "neturime"]):
                in_stock = False
        return txt, in_stock
    return None, None


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    desc_el = soup.find(id=lambda i: i and any(k in str(i).lower() for k in ["description", "aprasymas"]))
    if not desc_el:
        desc_el = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["product-description", "detailed-description", "overview"]))
    return clean_text(desc_el.get_text()) if desc_el else None


def _extract_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    imgs = []
    seen = set()
    gallery = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["gallery", "product-image", "media", "fotorama"]))
    search_scope = gallery if gallery else soup

    for img in search_scope.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-zoom-image")
        if src and not src.startswith("data:"):
            full = urljoin(base_url, src.strip())
            # Exclude small icons or logos
            if not any(x in full.lower() for x in ["logo", "icon", "placeholder", "badge"]):
                if full not in seen:
                    seen.add(full)
                    imgs.append(full)
    return imgs


def _extract_canonical_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    link = soup.find("link", rel=lambda r: r and "canonical" in r)
    if link and link.get("href"):
        return urljoin(base_url, link["href"].strip())
    return None
