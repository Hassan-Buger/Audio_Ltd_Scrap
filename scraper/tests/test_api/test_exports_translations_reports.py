"""Tests for exports, translations, reports, and search endpoints."""
from decimal import Decimal
from app.schemas.product import ProductCreate
from app.database.repositories.product_repo import ProductRepository


def test_exports_and_translations(client, db, auth_headers):
    # Seed a product
    p = ProductCreate(
        canonical_url="https://www.audiovideo.lt/audison-prima-ap4",
        title="Audison Prima AP 4",
        sku="AP-4",
        brand_name="Audison",
        price=Decimal("119.00"),
        description="Aukštos kokybės garsiakalbiai."
    )
    prod, _ = ProductRepository.upsert_product(db, p)
    db.commit()

    # CSV export
    csv_resp = client.get("/api/v1/exports/products/csv")
    assert csv_resp.status_code == 200
    assert "Audison Prima AP 4" in csv_resp.text
    assert "text/csv" in csv_resp.headers["content-type"]

    # JSON export
    json_resp = client.get("/api/v1/exports/products/json")
    assert json_resp.status_code == 200
    assert "Audison Prima AP 4" in json_resp.text

    # Reports
    overview_resp = client.get("/api/v1/reports/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json()["data"]["total_products"] == 1

    coverage_resp = client.get("/api/v1/reports/coverage")
    assert coverage_resp.status_code == 200

    completeness_resp = client.get("/api/v1/reports/completeness")
    assert completeness_resp.status_code == 200

    # Translation (preserves Lithuanian source)
    trans_resp = client.post(f"/api/v1/translations/products/{prod.id}", headers=auth_headers)
    assert trans_resp.status_code == 200
    assert trans_resp.json()["data"]["language"] == "en"

    # Verify source product remains in Lithuanian
    prod_check = ProductRepository.get_by_id(db, prod.id)
    assert prod_check.title == "Audison Prima AP 4"
    assert prod_check.description == "Aukštos kokybės garsiakalbiai."

    # Search endpoint
    search_resp = client.get("/api/v1/search/products?q=Audison")
    assert search_resp.status_code == 200
    assert len(search_resp.json()["data"]) == 1
