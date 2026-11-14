"""Controlled Playwright browser lifecycle manager."""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional
import logging

logger = logging.getLogger(__name__)


class PlaywrightManager:
    @staticmethod
    @asynccontextmanager
    async def get_browser_page(headless: bool = True) -> AsyncGenerator[Optional[object], None]:
        """
        Safely launch an isolated Chromium context asynchronously and yield page.
        Guarantees deterministic cleanup.
        """
        browser = None
        playwright = None
        try:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="lt-LT",
                viewport={"width": 1280, "height": 800}
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
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

    @staticmethod
    @contextmanager
    def get_sync_page(headless: bool = True) -> Generator[Optional[object], None, None]:
        """
        Safely launch an isolated Chromium context synchronously and yield page.
        Guarantees deterministic cleanup.
        """
        browser = None
        playwright = None
        try:
            from playwright.sync_api import sync_playwright
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="lt-LT",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            yield page
            try:
                context.close()
            except Exception:
                pass
        except ImportError:
            logger.warning("Playwright is not installed or available.")
            yield None
        except Exception as e:
            logger.error(f"Playwright sync execution error: {e}")
            yield None
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if playwright:
                try:
                    playwright.stop()
                except Exception:
                    pass
