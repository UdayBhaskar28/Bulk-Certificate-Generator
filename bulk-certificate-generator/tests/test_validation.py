def test_create_job_empty_recipients_fails(client):
    payload = {
        "title": "Introduction to AI",
        "issuer_name": "Tech Academy",
        "recipients": []
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_create_job_missing_title_fails(client):
    payload = {
        "issuer_name": "Tech Academy",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_create_job_blank_title_fails(client):
    payload = {
        "title": "   ",
        "issuer_name": "Tech Academy",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_create_job_missing_issuer_fails(client):
    payload = {
        "title": "Introduction to AI",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_get_nonexistent_job_returns_404(client):
    response = client.get("/api/v1/jobs/non-existent-uuid-99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_nonexistent_certificate_returns_404(client):
    response = client.get("/api/v1/certificates/non-existent-cert-99999")
    assert response.status_code == 404

def test_download_nonexistent_certificate_returns_404(client):
    response = client.get("/api/v1/certificates/non-existent-cert-99999/download")
    assert response.status_code == 404

def test_verify_nonexistent_certificate_returns_invalid(client):
    response = client.get("/api/v1/certificates/non-existent-cert-99999/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["verification_status"] == "NOT_FOUND"
