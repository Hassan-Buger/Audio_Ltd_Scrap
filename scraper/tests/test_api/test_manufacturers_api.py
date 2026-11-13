"""Tests for Manufacturers API."""
from app.schemas.manufacturer import ManufacturerCreate
from app.database.repositories.manufacturer_repo import ManufacturerRepository


def test_manufacturers_api(client, db, auth_headers):
    # Setup test manufacturer
    m = ManufacturerRepository.upsert_manufacturer(
        db, ManufacturerCreate(name="Hertz", slug="hertz", source_url="https://www.audiovideo.lt/gamintojai/hertz")
    )
    db.commit()

    # List
    list_resp = client.get("/api/v1/manufacturers")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 1
    assert list_resp.json()["data"][0]["name"] == "Hertz"

    # Detail
    get_resp = client.get(f"/api/v1/manufacturers/{m.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["slug"] == "hertz"

    # Coverage
    cov_resp = client.get("/api/v1/manufacturers/coverage")
    assert cov_resp.status_code == 200
    assert cov_resp.json()["data"]["total_manufacturers"] == 1

    # Discover (authorized)
    disc_resp = client.post("/api/v1/manufacturers/discover", headers=auth_headers)
    assert disc_resp.status_code == 202
    assert "job_id" in disc_resp.json()["data"]
