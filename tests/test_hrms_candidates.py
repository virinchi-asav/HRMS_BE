import io


async def test_candidate_apply_flow(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    job_payload = {
        "job_title": "QA Engineer",
        "employment_type": "Full-time",
        "location": "Remote",
        "department": "QA",
        "edu_qualification": "B.E/B.Tech",
        "key_skills": "Selenium",
        "job_description": "Test things.",
    }
    job_resp = await client.post("/api/hrms/jobs", json=job_payload, headers=headers)
    assert job_resp.status_code == 200, job_resp.text
    job_id = job_resp.json()["id"]

    resume_bytes = io.BytesIO(b"%PDF-1.4 fake resume content")
    form_data = {
        "job_id": str(job_id),
        "candidate_name": "John Applicant",
        "candidate_number": "9999999999",
        "candidate_email": "john.applicant@example.com",
        "candidate_doj": "20260801",
        "candidate_job_title": "QA Engineer",
    }
    files = {"resume": ("resume.pdf", resume_bytes, "application/pdf")}
    response = await client.post("/api/hrms/public/candidates/apply", data=form_data, files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job_id"] == job_id
    assert body["candidate_resume"].startswith("http")

    list_resp = await client.get("/api/hrms/candidates", headers=headers)
    assert any(c["candidate_email"] == "john.applicant@example.com" for c in list_resp.json())


async def test_candidate_apply_rejects_bad_resume_type(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    job_payload = {
        "job_title": "Designer",
        "employment_type": "Full-time",
        "location": "Remote",
        "department": "Design",
        "edu_qualification": "Any",
        "key_skills": "Figma",
        "job_description": "Design things.",
    }
    job_resp = await client.post("/api/hrms/jobs", json=job_payload, headers=headers)
    job_id = job_resp.json()["id"]

    bad_file = io.BytesIO(b"not a real resume")
    form_data = {
        "job_id": str(job_id),
        "candidate_name": "Bad Resume",
        "candidate_number": "1234567890",
        "candidate_email": "bad.resume@example.com",
        "candidate_doj": "20260801",
    }
    files = {"resume": ("resume.exe", bad_file, "application/octet-stream")}
    response = await client.post("/api/hrms/public/candidates/apply", data=form_data, files=files)
    assert response.status_code == 422
