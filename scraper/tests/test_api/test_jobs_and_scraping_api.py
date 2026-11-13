"""Tests for scraping jobs, control, and frontier endpoints."""


def test_scraping_control_and_jobs(client, auth_headers):
    # 1. Start scraping job
    start_resp = client.post("/api/v1/scraping/start", json={"scope": "full"}, headers=auth_headers)
    assert start_resp.status_code == 202
    job_id = start_resp.json()["data"]["job_id"]

    # 2. Get job details & progress
    job_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["data"]["id"] == job_id

    prog_resp = client.get(f"/api/v1/jobs/{job_id}/progress")
    assert prog_resp.status_code == 200
    assert prog_resp.json()["data"]["urls_discovered"] >= 4  # 4 initial seeds enqueued

    # 3. Frontier queue inspect
    queue_resp = client.get("/api/v1/crawl/queue")
    assert queue_resp.status_code == 200
    assert len(queue_resp.json()["data"]) >= 4

    # 4. Pause job
    pause_resp = client.post(f"/api/v1/scraping/pause/{job_id}", headers=auth_headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["data"]["status"] == "paused"

    # 5. Resume job
    resume_resp = client.post(f"/api/v1/scraping/resume/{job_id}", headers=auth_headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["data"]["status"] == "running"

    # 6. Cancel job
    cancel_resp = client.post(f"/api/v1/scraping/cancel/{job_id}", headers=auth_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["data"]["status"] == "cancelled"
