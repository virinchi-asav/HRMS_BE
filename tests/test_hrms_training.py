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
        json={**base_payload, "trainer_ids": [bu_head_id], "bu_head_id": bu_head_id},
        headers=admin_headers,
    )
    assert response.status_code == 400

    # A Team Member (wrong role) used as the approver should be rejected.
    response = await client.post(
        "/api/hrms/training",
        json={**base_payload, "trainer_ids": [trainer_id], "bu_head_id": trainer_id},
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
        "trainer_ids": [trainer_id],
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
        "trainer_ids": [trainer_id],
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
        "trainer_ids": [trainer_id],
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


async def test_training_supports_multiple_trainers(client, hrms_admin_token, hrms_user_factory):
    """Two Trainers on the same training - either one can act as Trainer (day-entries,
    materials, marking complete), and the response lists both."""
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_one_id, trainer_one_token = await hrms_user_factory("Trainer Five", "trainer5@example.com", 6)
    trainer_two_id, trainer_two_token = await hrms_user_factory("Trainer Six", "trainer6@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("Trainee Five", "trainee5@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("BU Five", "bu5@example.com", 7)

    payload = {
        "topic": "Pair Training",
        "description": "Two trainers co-teaching",
        "trainer_ids": [trainer_one_id, trainer_two_id],
        "trainee_ids": [trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
    }
    create_resp = await client.post("/api/hrms/training", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]
    trainer_ids_in_response = {t["id"] for t in create_resp.json()["trainers"]}
    assert trainer_ids_in_response == {trainer_one_id, trainer_two_id}

    trainer_one_headers = {"Authorization": f"Bearer {trainer_one_token}"}
    trainer_two_headers = {"Authorization": f"Bearer {trainer_two_token}"}
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}

    await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)

    # Trainer One logs a day entry.
    entry_one_resp = await client.post(
        f"/api/hrms/training/{training_id}/day-entries",
        json={"entry_date": "2026-11-01", "topic_covered": "Intro", "status": "COMPLETED"},
        headers=trainer_one_headers,
    )
    assert entry_one_resp.status_code == 200, entry_one_resp.text

    # Trainer Two (the other Trainer, not Trainer One) can also log a day entry.
    entry_two_resp = await client.post(
        f"/api/hrms/training/{training_id}/day-entries",
        json={"entry_date": "2026-11-02", "topic_covered": "Deep dive", "status": "COMPLETED"},
        headers=trainer_two_headers,
    )
    assert entry_two_resp.status_code == 200, entry_two_resp.text

    # The Trainee still cannot.
    trainee_entry_resp = await client.post(
        f"/api/hrms/training/{training_id}/day-entries",
        json={"entry_date": "2026-11-03", "topic_covered": "Should fail", "status": "COMPLETED"},
        headers=trainee_headers,
    )
    assert trainee_entry_resp.status_code == 404

    # Trainer Two (not the one who logged the first entry) marks it completed.
    complete_resp = await client.post(f"/api/hrms/training/{training_id}/complete", headers=trainer_two_headers)
    assert complete_resp.status_code == 200, complete_resp.text
    assert complete_resp.json()["status"] == "COMPLETED"

    # The list endpoint also reflects both trainers.
    list_resp = await client.get("/api/hrms/training", headers=admin_headers)
    item = next(t for t in list_resp.json()["content"] if t["id"] == training_id)
    assert set(item["trainer_ids"]) == {trainer_one_id, trainer_two_id}
    assert set(item["trainer_names"]) == {"Trainer Five", "Trainer Six"}


async def test_recording_permissions_and_list(client, hrms_admin_token, hrms_user_factory):
    """HR/Admin and any of the training's Trainers can add a recording (one per
    session, accumulating as a list); Trainees and the BU Head cannot. Deleting is
    restricted to whoever added it, or HR/Admin."""
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    hr_id, hr_token = await hrms_user_factory("HR Recording", "hr-recording@example.com", 2)
    trainer_id, trainer_token = await hrms_user_factory("Trainer Seven", "trainer7@example.com", 6)
    other_trainer_id, other_trainer_token = await hrms_user_factory("Trainer Eight", "trainer8@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("Trainee Six", "trainee6@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("BU Six", "bu6@example.com", 7)

    payload = {
        "topic": "Recording List Training",
        "trainer_ids": [trainer_id, other_trainer_id],
        "trainee_ids": [trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-12-01",
        "end_date": "2026-12-05",
    }
    create_resp = await client.post("/api/hrms/training", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]

    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}
    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    other_trainer_headers = {"Authorization": f"Bearer {other_trainer_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # Starts empty.
    empty_list_resp = await client.get(f"/api/hrms/training/{training_id}/recordings", headers=admin_headers)
    assert empty_list_resp.status_code == 200
    assert empty_list_resp.json() == []

    # Trainee cannot add one.
    trainee_resp = await client.post(
        f"/api/hrms/training/{training_id}/recordings",
        json={"title": "Should fail", "link_url": "https://sharepoint.example.com/should-fail"},
        headers=trainee_headers,
    )
    assert trainee_resp.status_code == 404

    # BU Head cannot add one either.
    bu_head_resp = await client.post(
        f"/api/hrms/training/{training_id}/recordings",
        json={"title": "Should fail", "link_url": "https://sharepoint.example.com/should-fail"},
        headers=bu_head_headers,
    )
    assert bu_head_resp.status_code == 404

    # Trainer One adds the Day 1 recording.
    day1_resp = await client.post(
        f"/api/hrms/training/{training_id}/recordings",
        json={"title": "Day 1", "link_url": "https://sharepoint.example.com/day1"},
        headers=trainer_headers,
    )
    assert day1_resp.status_code == 200, day1_resp.text
    day1 = day1_resp.json()
    assert day1["link_url"] == "https://sharepoint.example.com/day1"
    assert day1["added_by"] == trainer_id

    # Trainer Two (the other Trainer) adds the Day 2 recording.
    day2_resp = await client.post(
        f"/api/hrms/training/{training_id}/recordings",
        json={"title": "Day 2", "link_url": "https://sharepoint.example.com/day2"},
        headers=other_trainer_headers,
    )
    assert day2_resp.status_code == 200, day2_resp.text

    # HR adds one too.
    hr_resp = await client.post(
        f"/api/hrms/training/{training_id}/recordings",
        json={"title": "Wrap-up", "link_url": "https://sharepoint.example.com/wrapup"},
        headers=hr_headers,
    )
    assert hr_resp.status_code == 200, hr_resp.text

    # All three are listed, in order, visible to a participant (the Trainee).
    list_resp = await client.get(f"/api/hrms/training/{training_id}/recordings", headers=trainee_headers)
    assert list_resp.status_code == 200
    titles = [r["title"] for r in list_resp.json()]
    assert titles == ["Day 1", "Day 2", "Wrap-up"]

    # Trainer Two cannot delete Trainer One's recording (didn't add it, not HR/Admin).
    wrong_delete_resp = await client.delete(
        f"/api/hrms/training/{training_id}/recordings/{day1['id']}", headers=other_trainer_headers
    )
    assert wrong_delete_resp.status_code == 404

    # Trainer One can delete their own.
    own_delete_resp = await client.delete(
        f"/api/hrms/training/{training_id}/recordings/{day1['id']}", headers=trainer_headers
    )
    assert own_delete_resp.status_code == 200, own_delete_resp.text

    # HR/Admin can delete anyone's - e.g. Trainer Two's.
    admin_delete_resp = await client.delete(
        f"/api/hrms/training/{training_id}/recordings/{day2_resp.json()['id']}", headers=admin_headers
    )
    assert admin_delete_resp.status_code == 200, admin_delete_resp.text

    final_list_resp = await client.get(f"/api/hrms/training/{training_id}/recordings", headers=admin_headers)
    assert [r["title"] for r in final_list_resp.json()] == ["Wrap-up"]
