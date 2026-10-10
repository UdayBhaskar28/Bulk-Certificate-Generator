def test_create_and_process_bulk_job(client):
    payload = {
        "title": "Full-Stack Software Architecture",
        "issuer_name": "Cloud Computing Council",
        "issue_date": "October 10, 2026",
        "description": "Comprehensive engineering certification",
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com", "grade": "A"},
            {"name": "Bob Smith", "email": "bob@example.com", "grade": "A+"},
            {"name": "Charlie Brown", "email": "charlie@example.com", "grade": "B+"}
        ]
    }
    
    # 1. Create job
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_data = create_res.json()
    job_id = job_data["id"]
    assert job_id is not None
    assert job_data["total_count"] == 3

    # 2. Check completed job status
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    completed_data = status_res.json()
    
    assert completed_data["status"] == "COMPLETED"
    assert completed_data["total_count"] == 3
    assert completed_data["processed_count"] == 3
    assert completed_data["success_count"] == 3
    assert completed_data["failed_count"] == 0
    assert completed_data["progress_percentage"] == 100.0
    assert completed_data["download_all_url"] is not None

    # Check recipient items
    items = completed_data["certificates"]
    assert len(items) == 3
    for item in items:
        assert item["status"] == "COMPLETED"
        assert item["file_name"] is not None
        assert item["file_size"] > 1000
        assert item["download_url"] is not None
        assert item["preview_url"] is not None

def test_list_jobs(client):
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1

def test_get_job_items_endpoint(client):
    # First get the latest job ID from list
    jobs = client.get("/api/v1/jobs").json()
    job_id = jobs[0]["id"]

    response = client.get(f"/api/v1/jobs/{job_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert all(i["job_id"] == job_id for i in items)
