"""Pagination detection, next-page extraction, and loop prevention."""
import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qsl
from bs4 import BeautifulSoup
from .normalizers import clean_text


def extract_pagination(soup: BeautifulSoup, base_url: str) -> Tuple[Optional[int], Optional[int], List[str]]:
    """
    Extract current page, total pages (or last page), and all discovered pagination links.
    Returns: (current_page, total_pages, pagination_urls)
    """
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    pagination_urls: List[str] = []
    seen_urls = set()

    # Find pagination containers: .pages, .pagination, .pager, etc.
    pager_blocks = soup.find_all(class_=lambda c: c and any(k in str(c).lower() for k in ["pages", "pagination", "pager", "nav-page"]))
    
    for block in pager_blocks:
        # Detect current page (e.g. .current, .active, <strong>)
        curr = block.find(class_=lambda c: c and any(k in str(c).lower() for k in ["current", "active"]))
        if not curr:
            curr = block.find("strong")
        if curr:
            txt = clean_text(curr.get_text())
            if txt and txt.isdigit():
                current_page = int(txt)

        # Detect page links
        for a in block.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(base_url, href)
            txt = clean_text(a.get_text())
            
            # Check for page numbers in link text or query
            if txt and txt.isdigit():
                page_num = int(txt)
                if total_pages is None or page_num > total_pages:
                    total_pages = page_num
            else:
                # Check '?p=X' in query
                parsed = urlparse(full_url)
                params = dict(parse_qsl(parsed.query))
                if "p" in params and params["p"].isdigit():
                    page_num = int(params["p"])
                    if total_pages is None or page_num > total_pages:
                        total_pages = page_num

            if full_url not in seen_urls:
                seen_urls.add(full_url)
                pagination_urls.append(full_url)

    # If current_page couldn't be determined from DOM, check the base_url query param
    if current_page is None:
        parsed_base = urlparse(base_url)
        params_base = dict(parse_qsl(parsed_base.query))
        if "p" in params_base and params_base["p"].isdigit():
            current_page = int(params_base["p"])
        else:
            current_page = 1

    return current_page, total_pages, pagination_urls
