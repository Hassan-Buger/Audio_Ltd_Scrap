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

        all_cookies = []
        is_cleared = False
        challenge_titles = ["luktelėkite...", "just a moment...", "attention required! | cloudflare"]

        print("Browser is open. If you see a verification box ('Verify you are human'), click it.")
        print("Waiting for page to redirect to the store...\n")

        for i in range(120):
            time.sleep(1)
            try:
                title = page.title().strip().lower()
                cookies = context.cookies("https://www.audiovideo.lt/")
                has_clearance = any(c["name"] == "cf_clearance" for c in cookies)

                # Challenge is cleared once we have cookies AND the title is no longer a Cloudflare challenge interstitial
                if title and not any(ct in title for ct in challenge_titles) and (has_clearance or len(cookies) >= 2):
                    all_cookies = cookies
                    is_cleared = True
                    print(f"\n[SUCCESS] Page loaded store: '{page.title()}' (URL: {page.url})")
                    break
                elif i % 5 == 0:
                    print(f"  [{i}s] Waiting for verification... (Page title: '{page.title()}')")
            except Exception:
                pass

        try:
            # Short wait so any post-navigation cookies settle
            time.sleep(2)
            if not all_cookies:
                all_cookies = context.cookies("https://www.audiovideo.lt/")
            browser.close()
        except Exception:
            pass

        if is_cleared and all_cookies:
            # Build full cookie string (cf_clearance + session cookies)
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in all_cookies)
            print("\n[SUCCESS] Cloudflare clearance session cookies captured!")
            print(f"Cookies: {len(all_cookies)} cookie(s) captured.")
            print(f"Token snippet: {cookie_str[:60]}...")

            update_env_cookie(cookie_str)
            print(f"[SAVED] Updated SCRAPER_COOKIES in {ENV_PATH}")
            return cookie_str
        else:
            print("\n[TIMEOUT] Verification was not completed within 120 seconds.")
            return None


if __name__ == "__main__":
    capture_cf_cookie()
