"""Tests for Product catalogue API endpoints."""


def test_products_crud_and_lookup(client, auth_headers):
    # 1. Create a product (authorized)
    payload = {
        "canonical_url": "https://www.audiovideo.lt/test-product",
        "title": "Hertz Mille Legend ML 700.3",
        "sku": "ML-700-3",
        "ean": "8018823113423",
        "brand_name": "Hertz",
        "price": "349.00",
        "currency": "EUR",
        "in_stock": True,
        "description": "Aukščiausios kokybės garsiakalbiai.",
        "specifications": [
            {"label": "Galia", "value": "100 W", "numeric_value": "100", "unit": "W"}
        ]
    }
    create_resp = client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201
    created_data = create_resp.json()["data"]
    prod_id = created_data["id"]

    # 2. Unauthorized attempt without header must fail
    fail_resp = client.post("/api/v1/products", json=payload)
    assert fail_resp.status_code == 401

    # 3. List products
    list_resp = client.get("/api/v1/products")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) >= 1

    # 4. Lookup by ID
    get_resp = client.get(f"/api/v1/products/{prod_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["title"] == "Hertz Mille Legend ML 700.3"

    # 5. Lookup by SKU
    sku_resp = client.get("/api/v1/products/sku/ML-700-3")
    assert sku_resp.status_code == 200
    assert sku_resp.json()["data"]["id"] == prod_id

    # 6. Lookup by EAN
    ean_resp = client.get("/api/v1/products/ean/8018823113423")
    assert ean_resp.status_code == 200
    assert ean_resp.json()["data"]["id"] == prod_id

    # 7. Sub-resources: specifications & sources
    specs_resp = client.get(f"/api/v1/products/{prod_id}/specifications")
    assert specs_resp.status_code == 200
    assert len(specs_resp.json()["data"]) == 1

    # 8. Patch product
    patch_resp = client.patch(f"/api/v1/products/{prod_id}", json={"price": "329.00"}, headers=auth_headers)
    assert patch_resp.status_code == 200
    assert str(patch_resp.json()["data"]["price"]) == "329.00"

    # 9. Delete product
    del_resp = client.delete(f"/api/v1/products/{prod_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    # 10. Verify deleted
    assert client.get(f"/api/v1/products/{prod_id}").status_code == 404
