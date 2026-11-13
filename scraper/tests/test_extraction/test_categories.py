"""Tests for category tree, breadcrumb, and listing product extraction."""
from bs4 import BeautifulSoup
from app.extraction.categories import extract_category_tree, extract_listing_products


def test_extract_category_tree(sample_category_html):
    soup = BeautifulSoup(sample_category_html, "lxml")
    categories = extract_category_tree(soup, "https://www.audiovideo.lt/")
    
    assert len(categories) >= 2
    names = [c.name for c in categories]
    assert "Automobilių garso aparatūra" in names
    assert "Garso izoliacija" in names

    # Verify hierarchy level
    subcat = next(c for c in categories if c.name == "Garso izoliacija")
    assert subcat.level == 1
    assert subcat.slug == "automobiliu-garso-aparatura/garso-izoliacija"


def test_extract_listing_products(sample_category_html):
    soup = BeautifulSoup(sample_category_html, "lxml")
    prods = extract_listing_products(soup, "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija")
    
    assert len(prods) == 2
    assert "https://www.audiovideo.lt/vibrofiltr-profi-2-0mm-vibro-izoliacija" in prods
    assert "https://www.audiovideo.lt/sgm-techno-aliumast-alpha-2-izoliacija" in prods
