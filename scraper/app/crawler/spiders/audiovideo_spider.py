"""Scrapy Spider for Audiovideo.lt."""
import scrapy
from typing import Generator
from app.extraction.products import extract_product_detail
from app.extraction.categories import extract_category_tree, extract_listing_products
from app.extraction.pagination import extract_pagination
from app.crawler.url_normalizer import is_allowed_host, classify_url
from app.schemas.crawl import URLType


class AudiovideoSpider(scrapy.Spider):
    name = "audiovideo"
    allowed_domains = ["audiovideo.lt", "www.audiovideo.lt"]

    def __init__(self, job_id: int = 1, seed_urls: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = int(job_id)
        if seed_urls:
            self.start_urls = [u.strip() for u in seed_urls.split(",") if u.strip()]
        else:
            self.start_urls = [
                "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1",
                "https://www.audiovideo.lt/gamintojai/hertz",
                "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison",
                "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit"
            ]

    def parse(self, response: scrapy.http.Response) -> Generator:
        url = response.url
        html = response.text

        # Classify URL
        url_type = classify_url(url)

        if url_type == URLType.PRODUCT:
            prod_create = extract_product_detail(html, url)
            if prod_create:
                prod_create.crawl_job_id = self.job_id
                yield {"type": "product", "item": prod_create}
        else:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # Discover categories
            cats = extract_category_tree(soup, url)
            for cat in cats:
                yield {"type": "category", "item": cat}
                if is_allowed_host(cat.source_url):
                    yield scrapy.Request(cat.source_url, callback=self.parse)

            # Discover pagination
            _, _, page_urls = extract_pagination(soup, url)
            for p_url in page_urls:
                if is_allowed_host(p_url):
                    yield scrapy.Request(p_url, callback=self.parse)

            # Discover product URLs
            prod_urls = extract_listing_products(soup, url)
            for pr_url in prod_urls:
                if is_allowed_host(pr_url):
                    yield scrapy.Request(pr_url, callback=self.parse)
