"""Tests for Category tree and coverage API endpoints."""
from app.schemas.category import CategoryCreate
from app.database.repositories.category_repo import CategoryRepository


def test_categories_api(client, db, auth_headers):
    # Setup test categories
    c1 = CategoryRepository.upsert_category(
        db, CategoryCreate(name="Automobilių garso aparatūra", slug="automobiliu-garso-aparatura", source_url="https://www.audiovideo.lt/automobiliu-garso-aparatura", level=0)
    )
    c2 = CategoryRepository.upsert_category(
        db, CategoryCreate(name="Garso izoliacija", slug="automobiliu-garso-aparatura/garso-izoliacija", source_url="https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija", parent_id=c1.id, level=1)
    )
    db.commit()

    # List
    list_resp = client.get("/api/v1/categories")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 2

    # Tree
    tree_resp = client.get("/api/v1/categories/tree")
    assert tree_resp.status_code == 200
    roots = tree_resp.json()["data"]
    assert len(roots) == 1
    assert len(roots[0]["children"]) == 1

    # Children
    child_resp = client.get(f"/api/v1/categories/{c1.id}/children")
    assert child_resp.status_code == 200
    assert len(child_resp.json()["data"]) == 1

    # Coverage
    cov_resp = client.get("/api/v1/categories/coverage")
    assert cov_resp.status_code == 200
    assert cov_resp.json()["data"]["total_categories_discovered"] == 2

    # Trigger discovery (authorized)
    disc_resp = client.post("/api/v1/categories/discover", headers=auth_headers)
    assert disc_resp.status_code == 202
    assert "job_id" in disc_resp.json()["data"]
