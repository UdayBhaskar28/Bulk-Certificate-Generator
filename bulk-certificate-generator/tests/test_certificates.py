import io
import zipfile

def test_retrieve_and_download_certificate(client):
    # 1. Create a job
    payload = {
        "title": "Autonomous Agents Architecture",
        "issuer_name": "Antigravity Research Labs",
        "issue_date": "October 10, 2026",
        "recipients": [
            {"name": "Satoshi Nakamoto", "email": "satoshi@example.com", "grade": "Excellence"}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["id"]

    job_data = client.get(f"/api/v1/jobs/{job_id}").json()
    cert_item = job_data["certificates"][0]
    cert_id = cert_item["id"]

    # 2. Get certificate metadata
    meta_res = client.get(f"/api/v1/certificates/{cert_id}")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["id"] == cert_id
    assert meta["recipient_name"] == "Satoshi Nakamoto"
    assert meta["status"] == "COMPLETED"

    # 3. Download certificate PDF
    dl_res = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert "attachment" in dl_res.headers.get("content-disposition", "")
    assert dl_res.content.startswith(b"%PDF-")

    # 4. Preview certificate PDF
    prev_res = client.get(f"/api/v1/certificates/{cert_id}/preview")
    assert prev_res.status_code == 200
    assert prev_res.headers["content-type"] == "application/pdf"
    assert "inline" in prev_res.headers.get("content-disposition", "")
    assert prev_res.content.startswith(b"%PDF-")

def test_download_all_zip_archive(client):
    payload = {
        "title": "Distributed Systems & Cloud Networks",
        "issuer_name": "Network Foundation",
        "issue_date": "October 10, 2026",
        "recipients": [
            {"name": "Participant One", "email": "p1@example.com"},
            {"name": "Participant Two", "email": "p2@example.com"}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    # Download ZIP bundle
    zip_res = client.get(f"/api/v1/jobs/{job_id}/download-all")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert "attachment" in zip_res.headers.get("content-disposition", "")

    # Validate ZIP content
    zip_buffer = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        for fname in file_list:
            assert fname.endswith(".pdf")
            content = zf.read(fname)
            assert content.startswith(b"%PDF-")

def test_verify_certificate_endpoint(client):
    payload = {
        "title": "Machine Learning Security",
        "issuer_name": "Cyber Defense Council",
        "recipients": [
            {"name": "Radia Perlman", "email": "radia@example.com"}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    job_data = client.get(f"/api/v1/jobs/{job_id}").json()
    cert_id = job_data["certificates"][0]["id"]

    # Verify certificate
    verify_res = client.get(f"/api/v1/certificates/{cert_id}/verify")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()

    assert verify_data["valid"] is True
    assert verify_data["certificate_id"] == cert_id
    assert verify_data["recipient_name"] == "Radia Perlman"
    assert verify_data["title"] == "Machine Learning Security"
    assert verify_data["issuer_name"] == "Cyber Defense Council"
    assert verify_data["verification_status"] == "VERIFIED_AUTHENTIC"
    assert verify_data["download_url"] is not None
