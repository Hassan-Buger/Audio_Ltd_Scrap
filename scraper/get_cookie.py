"""
Interactive helper to obtain Cloudflare clearance cookie.
Launches a visible browser window where the user can complete the verification challenge.
Once completed, the cookie is automatically saved to scraper/.env.
"""
import time
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ENV_PATH = Path(__file__).resolve().parent / ".env"


def update_env_cookie(cookie_str: str):
    """Write or update the SCRAPER_COOKIES line in .env file."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"SCRAPER_COOKIES={cookie_str}\n", encoding="utf-8")
        return

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("SCRAPER_COOKIES="):
            new_lines.append(f"SCRAPER_COOKIES={cookie_str}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"SCRAPER_COOKIES={cookie_str}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def capture_cf_cookie():
    print("=================================================================")
    print("  Audiovideo.lt Cloudflare Clearance Capturer")
    print("=================================================================")
    print("Launching visible browser window...")
    print("Please complete the Cloudflare 'Verify you are human' box if shown.")
    print("Waiting for clearance cookie...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="lt-LT",
            no_viewport=True
        )
        page = context.new_page()

        try:
            page.goto("https://www.audiovideo.lt/", timeout=60000)
        except Exception as e:
            print(f"Navigation notice: {e}")

        clearance_cookie = None
        for i in range(120):
            try:
                cookies = context.cookies("https://www.audiovideo.lt/")
                for c in cookies:
                    if c["name"] == "cf_clearance":
                        clearance_cookie = c["value"]
                        break
            except Exception:
                pass

            if clearance_cookie:
                break
            time.sleep(1)

        try:
            browser.close()
        except Exception:
            pass

        if clearance_cookie:
            print("\n[SUCCESS] cf_clearance cookie captured!")
            cookie_str = f"cf_clearance={clearance_cookie}"
            print(f"Token: {cookie_str[:40]}...")

            update_env_cookie(cookie_str)
            print(f"[SAVED] Updated SCRAPER_COOKIES in {ENV_PATH}")
            return cookie_str
        else:
            print("\n[TIMEOUT] cf_clearance cookie was not detected within 120 seconds.")
            return None


if __name__ == "__main__":
    capture_cf_cookie()
