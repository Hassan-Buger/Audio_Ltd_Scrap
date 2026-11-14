"""Seed raw HTML snapshots from test fixtures so the crawler can parse and demonstrate offline."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.raw_store import raw_store

FIXTURE_DIR = Path(__file__).resolve().parent / "data" / "fixtures"

fixtures_map = {
    "https://www.audiovideo.lt/": "home.html",
    "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija": "category_p1.html",
    "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1": "category_p1.html",
    "https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=2": "category_p2.html",
    "https://www.audiovideo.lt/prod-a.html": "product_a.html",
    "https://www.audiovideo.lt/prod-b.html": "product_b.html",
    "https://www.audiovideo.lt/prod-b.html?utm_medium=cpc": "product_b.html",
    "https://www.audiovideo.lt/prod-c.html": "product_c_no_name.html",
    "https://www.audiovideo.lt/gamintojai/hertz": "category_p1.html",
    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison": "category_p1.html",
    "https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit": "category_p2.html",
}

def seed_offline_fixtures():
    count = 0
    for url, filename in fixtures_map.items():
        file_path = FIXTURE_DIR / filename
        if file_path.exists():
            raw_store.ingest_file(url, file_path)
            count += 1
    return count

if __name__ == "__main__":
    count = seed_offline_fixtures()
    print(f"Seeded {count} fixture snapshots from {FIXTURE_DIR}")
