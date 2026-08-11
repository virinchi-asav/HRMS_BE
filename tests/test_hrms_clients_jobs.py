async def test_clients_require_admin(client):
    response = await client.get("/api/hrms/clients")
    assert response.status_code == 401


async def test_client_crud_and_username_derivation(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    payload = {"firstname": "Jane", "lastname": "Doe", "email": "jane.doe@acme.com", "organization": "Acme"}
    response = await client.post("/api/hrms/clients", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["username"] == "jane.doe"

    client_id = body["id"]
    delete_resp = await client.delete(f"/api/hrms/clients/{client_id}", headers=headers)
    assert delete_resp.status_code == 200

    # soft-deleted - should 404 now
    get_resp = await client.get(f"/api/hrms/clients/{client_id}", headers=headers)
    assert get_resp.status_code == 404

    restore_resp = await client.post(f"/api/hrms/clients/{client_id}/restore", headers=headers)
    assert restore_resp.status_code == 200

    get_after_restore = await client.get(f"/api/hrms/clients/{client_id}", headers=headers)
    assert get_after_restore.status_code == 200


async def test_job_crud_and_soft_delete_visible_in_list(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    payload = {
        "job_title": "Backend Engineer",
        "employment_type": "Full-time",
        "location": "Remote",
        "department": "Engineering",
        "edu_qualification": "B.E/B.Tech",
        "key_skills": "Python, FastAPI",
        "job_description": "Build things.",
    }
    create_resp = await client.post("/api/hrms/jobs", json=payload, headers=headers)
    assert create_resp.status_code == 200, create_resp.text
    job_id = create_resp.json()["id"]

    public_list = await client.get("/api/hrms/public/jobs")
    assert any(j["id"] == job_id for j in public_list.json())

    delete_resp = await client.delete(f"/api/hrms/jobs/{job_id}", headers=headers)
    assert delete_resp.status_code == 200

    # Public careers listing excludes soft-deleted jobs...
    public_list_after = await client.get("/api/hrms/public/jobs")
    assert all(j["id"] != job_id for j in public_list_after.json())

    # ...but the admin list (JobsController::index parity) still shows it, for restore.
    admin_list = await client.get("/api/hrms/jobs", headers=headers)
    assert any(j["id"] == job_id for j in admin_list.json())
