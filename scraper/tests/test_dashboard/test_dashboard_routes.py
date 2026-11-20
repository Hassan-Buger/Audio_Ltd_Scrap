"""Tests for Operator Dashboard HTML routes."""


def test_dashboard_routes(client):
    # Overview
    r1 = client.get("/dashboard")
    assert r1.status_code == 200
    assert "Catalogue Operations Overview" in r1.text

    # Jobs page
    r2 = client.get("/dashboard/jobs")
    assert r2.status_code == 200
    assert "Crawl & Scraping Jobs" in r2.text

    # Products page
    r3 = client.get("/dashboard/products")
    assert r3.status_code == 200
    assert "Product Catalogue" in r3.text

    # Categories page
    r4 = client.get("/dashboard/categories")
    assert r4.status_code == 200
    assert "Category Tree & Coverage" in r4.text

    # Failures page
    r5 = client.get("/dashboard/failures")
    assert r5.status_code == 200
    assert "Failures & Inaccessible URLs" in r5.text

    # Reports page
    r6 = client.get("/dashboard/reports")
    assert r6.status_code == 200
    assert "Reports & Data Quality" in r6.text

    # Root redirect
    r_root = client.get("/", follow_redirects=False)
    assert r_root.status_code == 302
    assert r_root.headers["location"] == "/docs"
