"""Controlled Playwright browser lifecycle manager."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)


class PlaywrightManager:
    @staticmethod
    @asynccontextmanager
    async def get_browser_page(headless: bool = True) -> AsyncGenerator[Optional[object], None]:
        """
        Safely launch an isolated Chromium context and yield page.
        Guarantees deterministic cleanup.
        """
        browser = None
        playwright = None
        try:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="lt-LT"
            )
            page = await context.new_page()
            yield page
            await context.close()
        except ImportError:
            logger.warning("Playwright is not installed or available.")
            yield None
        except Exception as e:
            logger.error(f"Playwright execution error: {e}")
            yield None
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
