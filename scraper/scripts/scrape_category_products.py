#!/usr/bin/env python3
"""
Automated Product Crawler & Ingestion Tool.

Crawls individual product detail pages from Audiovideo.lt and posts full HTML snapshots
(with description, specifications table, and gallery images) directly to the Railway API.
"""
import os
import sys
import time
import argparse
import zipfile
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

DEFAULT_TARGETS = [
    "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1",
    "https://www.audiovideo.lt/gamintojai/hertz",
    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison",
    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit",
]

DEFAULT_API = os.getenv("API_URL", "https://audioltdscrap-production-540ccae2.up.railway.app")
DEFAULT_KEY = os.getenv("API_KEY", "")


def fetch_incomplete_urls_from_api(api_url: str) -> List[str]:
    """Fetch all product URLs from the API where is_complete is False."""
    urls: List[str] = []
    page = 1
    while True:
        resp = httpx.get(
            f"{api_url.rstrip('/')}/api/v1/products",
            params={"page": page, "limit": 200},
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("data", [])
        if not items:
            break
        for item in items:
            if not item.get("is_complete"):
                u = item.get("source_url") or item.get("canonical_url")
                if u:
                    urls.append(u)
        meta = payload.get("meta") or {}
        if page >= (meta.get("total_pages") or 1):
            break
        page += 1
    return urls


def extract_product_links_from_category(html: str, base_url: str) -> List[str]:
    """Extract individual product links from a category listing HTML."""
    soup = BeautifulSoup(html, "lxml")
    links: Set[str] = set()
    cards = soup.select(".products-grid .item, .products-list .item, li.item, .product-item")
    for card in cards:
        a = card.select_one(".product-name a, .product-item-link, a.title, h2 a, h3 a")
        if not a:
            a = card.find("a", href=True)
        if a and a.get("href"):
            full = urljoin(base_url, a["href"].strip())
            # Exclude search, cart, and non-product URLs
            if not any(x in full for x in ["checkout", "cart", "catalogsearch", "?dir=", "?order="]):
                links.add(full)
    return sorted(list(links))


def push_snapshot_to_api(api_url: str, api_key: str, product_url: str, html_content: str) -> bool:
    """Send product HTML snapshot to Railway API."""
    endpoint = f"{api_url.rstrip('/')}/api/v1/scraping/snapshot-and-scrape"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "url": product_url,
        "html_content": html_content,
        "force_refresh": True
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                prod = data.get("product", {})
                print(f"  [SUCCESS] Ingested: {prod.get('title', product_url)} | Specs: {prod.get('specifications_count', 0)} | Images: {prod.get('images_count', 0)}")
                return True
            else:
                print(f"  [ERROR {resp.status_code}] Failed for {product_url}: {resp.text[:150]}")
                return False
    except Exception as e:
        print(f"  [EXCEPTION] {product_url}: {e}")
        return False


def crawl_with_playwright(product_urls: List[str], api_url: str, api_key: str, output_zip: str = None):
    """Crawl product URLs using Playwright browser and ingest into Railway API."""
    from playwright.sync_api import sync_playwright

    print(f"\nLaunching Playwright browser session for {len(product_urls)} products...")
    zf = zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) if output_zip else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headless false helps residential sessions pass Turnstile
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for idx, purl in enumerate(product_urls, 1):
            print(f"[{idx}/{len(product_urls)}] Navigating to {purl}...")
            try:
                page.goto(purl, wait_until="domcontentloaded", timeout=30000)
                # Wait briefly for specifications and gallery images to mount
                time.sleep(1.5)
                html = page.content()

                if zf:
                    fname = f"product_{idx}.html"
                    zf.writestr(fname, html)
                    print(f"  Saved to archive as {fname}")

                if api_key:
                    push_snapshot_to_api(api_url, api_key, purl, html)
            except Exception as e:
                print(f"  Failed loading {purl}: {e}")

        browser.close()

    if zf:
        zf.close()
        print(f"\nSaved all product HTML snapshots into archive: {output_zip}")


def main():
    parser = argparse.ArgumentParser(description="Audiovideo.lt Product Detail Ingestion Script")
    parser.add_argument("--category-file", help="Path to local category HTML file to extract product URLs from")
    parser.add_argument("--from-api", action="store_true", help="Fetch incomplete product URLs directly from the API")
    parser.add_argument("--api-url", default=DEFAULT_API, help="Base URL of Railway API")
    parser.add_argument("--api-key", default=DEFAULT_KEY, help="Operator API key")
    parser.add_argument("--zip-output", default="products_batch.zip", help="Zip file to save HTML snapshots into")
    args = parser.parse_args()

    urls = []
    if args.from_api:
        urls = fetch_incomplete_urls_from_api(args.api_url)
        print(f"Fetched {len(urls)} incomplete product URLs from {args.api_url}")
    elif args.category_file:
        p = Path(args.category_file)
        if p.exists():
            html = p.read_text(encoding="utf-8", errors="replace")
            urls = extract_product_links_from_category(html, "https://www.audiovideo.lt/")
            print(f"Extracted {len(urls)} product URLs from {p}")

    if not urls:
        print("No product URLs found. Provide --from-api or --category-file <path_to_saved_category.html>")
        return

    crawl_with_playwright(urls, args.api_url, args.api_key, args.zip_output)


if __name__ == "__main__":
    main()
