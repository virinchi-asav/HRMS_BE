async def test_training_requires_auth(client):
    response = await client.get("/api/hrms/training")
    assert response.status_code == 401


async def test_create_training_rejects_wrong_roles(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, _ = await hrms_user_factory("Trainer One", "trainer1@example.com", 6)
    trainee_id, _ = await hrms_user_factory("Trainee One", "trainee1@example.com", 6)
    bu_head_id, _ = await hrms_user_factory("BU One", "bu1@example.com", 7)

    base_payload = {
        "topic": "Onboarding",
        "description": "Intro training",
        "trainee_ids": [trainee_id],
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
    }

    # A BU Head (wrong role) used as the Trainer should be rejected.
    response = await client.post(
        "/api/hrms/training",
        json={**base_payload, "trainer_id": bu_head_id, "bu_head_id": bu_head_id},
        headers=admin_headers,
    )
    assert response.status_code == 400

    # A Team Member (wrong role) used as the approver should be rejected.
    response = await client.post(
        "/api/hrms/training",
        json={**base_payload, "trainer_id": trainer_id, "bu_head_id": trainer_id},
        headers=admin_headers,
    )
    assert response.status_code == 400


async def test_training_reject_flow(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, _ = await hrms_user_factory("Trainer Two", "trainer2@example.com", 6)
    trainee_id, _ = await hrms_user_factory("Trainee Two", "trainee2@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("BU Two", "bu2@example.com", 7)

    payload = {
        "topic": "Security Basics",
        "description": "Covers password hygiene",
        "trainer_id": trainer_id,
        "trainee_ids": [trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-02-01",
        "end_date": "2026-02-05",
    }
    create_resp = await client.post("/api/hrms/training", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "PENDING_APPROVAL"

    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}
    reject_resp = await client.post(
        f"/api/hrms/training/{training_id}/reject", json={"reason": "Not needed right now"}, headers=bu_head_headers
    )
    assert reject_resp.status_code == 200, reject_resp.text
    assert reject_resp.json()["status"] == "REJECTED"
    assert reject_resp.json()["rejection_reason"] == "Not needed right now"


async def test_training_full_approval_and_completion_flow(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, trainer_token = await hrms_user_factory("Trainer Three", "trainer3@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("Trainee Three", "trainee3@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("BU Three", "bu3@example.com", 7)

    payload = {
        "topic": "API Design",
        "description": "REST fundamentals",
        "trainer_id": trainer_id,
        "trainee_ids": [trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-03-01",
        "end_date": "2026-03-05",
    }
    create_resp = await client.post("/api/hrms/training", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]

    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}

    # Trainer can't see it (or act on it) until approved.
    pre_approval_list = await client.get("/api/hrms/training", headers=trainer_headers)
    assert all(item["id"] != training_id for item in pre_approval_list.json()["content"])

    approve_resp = await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "APPROVED"

    # Now the Trainer can see it.
    post_approval_list = await client.get("/api/hrms/training", headers=trainer_headers)
    assert any(item["id"] == training_id for item in post_approval_list.json()["content"])

    day_entry_resp = await client.post(
        f"/api/hrms/training/{training_id}/day-entries",
        json={"entry_date": "2026-03-01", "topic_covered": "HTTP verbs", "status": "COMPLETED"},
        headers=trainer_headers,
    )
    assert day_entry_resp.status_code == 200, day_entry_resp.text

    # Trainee cannot add a day entry (Trainer-only action).
    trainee_day_entry_resp = await client.post(
        f"/api/hrms/training/{training_id}/day-entries",
        json={"entry_date": "2026-03-02", "topic_covered": "Status codes", "status": "COMPLETED"},
        headers=trainee_headers,
    )
    assert trainee_day_entry_resp.status_code == 404

    comment_resp = await client.post(
        f"/api/hrms/training/{training_id}/comments", json={"comment": "Great session!"}, headers=trainee_headers
    )
    assert comment_resp.status_code == 200, comment_resp.text

    complete_resp = await client.post(f"/api/hrms/training/{training_id}/complete", headers=trainer_headers)
    assert complete_resp.status_code == 200, complete_resp.text
    assert complete_resp.json()["status"] == "COMPLETED"

    # HR/Admin and the BU Head can see the completed status.
    admin_get = await client.get(f"/api/hrms/training/{training_id}", headers=admin_headers)
    assert admin_get.json()["status"] == "COMPLETED"
    bu_head_get = await client.get(f"/api/hrms/training/{training_id}", headers=bu_head_headers)
    assert bu_head_get.json()["status"] == "COMPLETED"

    entries = await client.get(f"/api/hrms/training/{training_id}/day-entries", headers=admin_headers)
    assert len(entries.json()) == 1
    comments = await client.get(f"/api/hrms/training/{training_id}/comments", headers=admin_headers)
    assert len(comments.json()) == 1


async def test_training_materials_link_and_document(client, hrms_admin_token, hrms_user_factory):
    import shutil

    from app.hrms.services import file_storage_service

    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, trainer_token = await hrms_user_factory("Trainer Four", "trainer4@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("Trainee Four", "trainee4@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("BU Four", "bu4@example.com", 7)

    payload = {
        "topic": "Cloud Basics",
        "description": "Intro to cloud",
        "trainer_id": trainer_id,
        "trainee_ids": [trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-04-01",
        "end_date": "2026-04-05",
    }
    create_resp = await client.post("/api/hrms/training", json=payload, headers=admin_headers)
    training_id = create_resp.json()["id"]

    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}

    # Materials cannot be added while still pending approval.
    early_link_resp = await client.post(
        f"/api/hrms/training/{training_id}/materials",
        json={"title": "Slides", "link_url": "https://example.com/slides"},
        headers=trainer_headers,
    )
    assert early_link_resp.status_code == 404

    await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)

    link_resp = await client.post(
        f"/api/hrms/training/{training_id}/materials",
        json={"title": "Reference Slides", "link_url": "https://example.com/slides"},
        headers=trainer_headers,
    )
    assert link_resp.status_code == 200, link_resp.text
    assert link_resp.json()["material_type"] == "LINK"
    assert link_resp.json()["link_url"] == "https://example.com/slides"

    # Only the Trainer can attach materials, not the Trainee.
    trainee_link_resp = await client.post(
        f"/api/hrms/training/{training_id}/materials",
        json={"title": "Should fail", "link_url": "https://example.com/x"},
        headers=trainee_headers,
    )
    assert trainee_link_resp.status_code == 404

    try:
        upload_resp = await client.post(
            f"/api/hrms/training/{training_id}/materials/upload",
            data={"title": "Handout"},
            files={"file": ("handout.txt", b"hello world", "text/plain")},
            headers=trainer_headers,
        )
        assert upload_resp.status_code == 200, upload_resp.text
        assert upload_resp.json()["material_type"] == "DOCUMENT"
        assert upload_resp.json()["file_url"] is not None

        # The Trainee (a participant) can see both materials.
        trainee_list_resp = await client.get(
            f"/api/hrms/training/{training_id}/materials", headers=trainee_headers
        )
        assert trainee_list_resp.status_code == 200
        materials = trainee_list_resp.json()
        assert {m["material_type"] for m in materials} == {"LINK", "DOCUMENT"}
    finally:
        shutil.rmtree(file_storage_service.training_material_dir(training_id), ignore_errors=True)
