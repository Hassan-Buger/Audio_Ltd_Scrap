"""Tests for pagination detection and loop prevention."""
from bs4 import BeautifulSoup
from app.extraction.pagination import extract_pagination


def test_extract_pagination(sample_category_html):
    soup = BeautifulSoup(sample_category_html, "lxml")
    curr_page, total_pages, urls = extract_pagination(
        soup, "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija"
    )
    assert curr_page == 1
    assert total_pages == 3
    assert len(urls) == 2
    assert "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=2" in urls
    assert "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=3" in urls
