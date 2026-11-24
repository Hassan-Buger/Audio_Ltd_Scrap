"""Tests for media proxy endpoint and WooCommerce product schema formatting."""
import pytest
from app.api.routes.media import rewrite_image_url


def test_rewrite_image_url():
    original = "https://www.audiovideo.lt/media/catalog/product/8/9/890sp25a_2.jpg"
    rewritten = rewrite_image_url(original, "https://audioltdscrap-production.up.railway.app")
    assert rewritten == "https://audioltdscrap-production.up.railway.app/media/catalog/product/8/9/890sp25a_2.jpg"


def test_media_serve_placeholder(client):
    """Test that requesting a missing product image returns the fallback SVG with HTTP 200 (never 403)."""
    resp = client.get("/media/catalog/product/nonexistent/sample.jpg")
    assert resp.status_code == 200
    assert "svg" in resp.headers.get("content-type", "")
    assert b"<svg" in resp.content


def test_products_category_filter_and_woocommerce_format(client, auth_headers):
    """Test creating a product and querying it with the category query filter and checking WooCommerce fields."""
    payload = {
        "canonical_url": "https://www.audiovideo.lt/bass-habit-spl-play-sp25a",
        "title": "Bass Habit SPL Play SP25A",
        "sku": "SP25A",
        "brand_name": "Bass Habit",
        "price": "15.00",
        "regular_price": "20.00",
        "currency": "EUR",
        "in_stock": True,
        "description": "<p>High performance tweeter</p>",
        "images": ["https://www.audiovideo.lt/media/catalog/product/8/9/890sp25a_2.jpg"],
        "specifications": [
            {"label": "Manufacturer", "value": "Bass Habit"},
            {"label": "Impedance", "value": "4 Ohm"}
        ]
    }
    create_resp = client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201
    created_data = create_resp.json()["data"]
    assert created_data["sku"] == "SP25A"
    assert created_data["source_id"] is not None
    assert created_data["brand"] == "Bass Habit"
    assert len(created_data["specifications"]) == 2
    assert "media/catalog/product" in created_data["images"][0]

    # Query by category/brand filter
    list_resp = client.get("/api/v1/products?category=bass-habit")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert len(items) >= 1
    found = any(p["sku"] == "SP25A" for p in items)
    assert found
