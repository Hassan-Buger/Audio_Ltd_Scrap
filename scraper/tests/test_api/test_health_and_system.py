"""Tests for Health and System status API endpoints."""


def test_health_endpoints(client):
    # App health
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"

    # Dependency readiness
    resp_ready = client.get("/api/v1/health/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["success"] is True

    # System status & stats
    resp_status = client.get("/api/v1/system/status")
    assert resp_status.status_code == 200
    assert resp_status.json()["data"]["status"] == "operational"

    resp_stats = client.get("/api/v1/system/stats")
    assert resp_stats.status_code == 200
    assert "total_products" in resp_stats.json()["data"]

    # Top-level aliases
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
