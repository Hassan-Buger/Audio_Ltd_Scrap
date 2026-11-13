"""Scrapy configuration settings."""
from app.config import settings

BOT_NAME = "audiovideo_scraper"

SPIDER_MODULES = ["app.crawler.spiders"]
NEWSPIDER_MODULE = "app.crawler.spiders"

# Politeness and limits
USER_AGENT = settings.SCRAPER_USER_AGENT
ROBOTSTXT_OBEY = False  # Obey policy handled in frontier & reconnaissance
CONCURRENT_REQUESTS = settings.CRAWL_CONCURRENCY
DOWNLOAD_DELAY = settings.CRAWL_DOWNLOAD_DELAY
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lt,en-US;q=0.7,en;q=0.3",
}

ITEM_PIPELINES = {
    "app.crawler.pipelines.db_pipeline.DatabasePipeline": 300,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
