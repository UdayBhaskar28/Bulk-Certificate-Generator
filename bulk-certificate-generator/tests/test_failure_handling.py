def test_individual_failure_isolation_allows_other_certificates_to_succeed(client):
    """
    Validates requirement:
    'A failure while generating one certificate should not unnecessarily prevent
    other valid certificates in the same job from being generated.'
    'The job status should provide enough information to identify successful and failed generations.'
    """
    payload = {
        "title": "Systems Engineering Specialization",
        "issuer_name": "DeepMind Systems Lab",
        "recipients": [
            # 1. Valid recipient
            {
                "name": "Grace Hopper",
                "email": "grace.hopper@example.com",
                "grade": "Distinction"
            },
            # 2. Invalid recipient (blank name)
            {
                "name": "   ",
                "email": "no.name@example.com"
            },
            # 3. Invalid recipient (malformed email format)
            {
                "name": "Invalid Email User",
                "email": "definitely-not-an-email"
            },
            # 4. Valid recipient
            {
                "name": "Margaret Hamilton",
                "email": "margaret.hamilton@example.com",
                "grade": "Honors"
            }
        ]
    }

    # Submit job
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    # Retrieve completed job
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    # Verify overall metrics
    assert job_data["status"] == "PARTIALLY_COMPLETED"
    assert job_data["total_count"] == 4
    assert job_data["processed_count"] == 4
    assert job_data["success_count"] == 2
    assert job_data["failed_count"] == 2
    assert "failed generation" in job_data["error_summary"].lower()

    # Verify per-recipient statuses
    items = job_data["certificates"]
    assert len(items) == 4

    # Grace Hopper must have succeeded
    grace = next(i for i in items if i["recipient_email"] == "grace.hopper@example.com")
    assert grace["status"] == "COMPLETED"
    assert grace["file_name"] is not None
    assert grace["file_size"] > 1000
    assert grace["error_message"] is None

    # Margaret Hamilton must have succeeded
    margaret = next(i for i in items if i["recipient_email"] == "margaret.hamilton@example.com")
    assert margaret["status"] == "COMPLETED"
    assert margaret["file_name"] is not None
    assert margaret["file_size"] > 1000
    assert margaret["error_message"] is None

    # Empty name recipient must have failed with an informative error
    blank_name_item = next(i for i in items if i["recipient_email"] == "no.name@example.com")
    assert blank_name_item["status"] == "FAILED"
    assert blank_name_item["error_message"] is not None
    assert "name" in blank_name_item["error_message"].lower()

    # Invalid email recipient must have failed with an informative error
    bad_email_item = next(i for i in items if i["recipient_name"] == "Invalid Email User")
    assert bad_email_item["status"] == "FAILED"
    assert bad_email_item["error_message"] is not None
    assert "email" in bad_email_item["error_message"].lower()

def test_job_with_all_invalid_recipients_becomes_failed(client):
    payload = {
        "title": "Quantum Computing",
        "issuer_name": "Quantum Lab",
        "recipients": [
            {"name": "", "email": "bad1@example.com"},
            {"name": "Bad Email", "email": "invalid-address"}
        ]
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    job_data = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job_data["status"] == "FAILED"
    assert job_data["success_count"] == 0
    assert job_data["failed_count"] == 2
