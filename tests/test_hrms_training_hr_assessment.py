import pytest

from app.core.exceptions import UserUnauthorizedException


async def _create_bank_with_mcq(client, headers):
    bank_resp = await client.post("/api/hrms/task-assessments/banks", json={"name": "HR Bank"}, headers=headers)
    assert bank_resp.status_code == 200, bank_resp.text
    bank_id = bank_resp.json()["id"]

    q_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "M",
            "question_type": "MULTIPLE_CHOICE",
            "question_text": "2 + 2 = ?",
            "options": [{"option_text": "4", "is_correct": True}, {"option_text": "5", "is_correct": False}],
        },
        headers=headers,
    )
    assert q_resp.status_code == 200, q_resp.text
    return q_resp.json()["id"]


async def test_training_assessment_given_by_validation(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, _ = await hrms_user_factory("HR-flow Trainer", "hrflow-trainer1@example.com", 6)
    trainee_id, _ = await hrms_user_factory("HR-flow Trainee", "hrflow-trainee1@example.com", 6)
    bu_head_id, _ = await hrms_user_factory("HR-flow BU", "hrflow-bu1@example.com", 7)

    base_payload = {
        "topic": "Invalid Given-By",
        "trainer_id": trainer_id,
        "trainee_ids": [trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-05-01",
        "end_date": "2026-05-05",
        "has_assessment": True,
        "assessment_given_by": "SOMEONE_ELSE",
    }
    resp = await client.post("/api/hrms/training", json=base_payload, headers=admin_headers)
    assert resp.status_code == 400


async def test_hr_given_assessment_full_flow(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, trainer_token = await hrms_user_factory("HR-flow Trainer2", "hrflow-trainer2@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("HR-flow Trainee2", "hrflow-trainee2@example.com", 6)
    other_trainee_id, _ = await hrms_user_factory("HR-flow Other Trainee", "hrflow-other-trainee@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("HR-flow BU2", "hrflow-bu2@example.com", 7)

    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}

    create_resp = await client.post(
        "/api/hrms/training",
        json={
            "topic": "HR-Given Assessment Training",
            "trainer_id": trainer_id,
            "trainee_ids": [trainee_id],
            "bu_head_id": bu_head_id,
            "start_date": "2026-06-01",
            "end_date": "2026-06-05",
            "has_assessment": True,
            "assessment_given_by": "HR",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]
    assert create_resp.json()["assessment_given_by"] == "HR"

    await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)

    # The Trainer's old-style project-review assessment is disabled when HR was chosen.
    old_flow_resp = await client.post(
        f"/api/hrms/training/{training_id}/assessments",
        data={"trainee_id": str(trainee_id), "description": "Should be rejected"},
        headers=trainer_headers,
    )
    assert old_flow_resp.status_code == 400

    question_id = await _create_bank_with_mcq(client, admin_headers)

    # HR cannot give the Task Assessment before the Trainer marks the training completed.
    early_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Should fail - not completed yet",
            "training_id": training_id,
            "time_limit_minutes": 10,
            "question_ids": [question_id],
            "trainee_ids": [trainee_id],
        },
        headers=admin_headers,
    )
    assert early_resp.status_code == 400

    complete_resp = await client.post(f"/api/hrms/training/{training_id}/complete", headers=trainer_headers)
    assert complete_resp.status_code == 200, complete_resp.text

    # A trainee not part of this training can't be assigned via the training-linked task.
    wrong_trainee_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Should fail - wrong trainee",
            "training_id": training_id,
            "time_limit_minutes": 10,
            "question_ids": [question_id],
            "trainee_ids": [other_trainee_id],
        },
        headers=admin_headers,
    )
    assert wrong_trainee_resp.status_code == 400

    # Now HR can give the Task Assessment for the actual trainee.
    task_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "HR Assessment for HR-flow Trainee2",
            "training_id": training_id,
            "time_limit_minutes": 10,
            "question_ids": [question_id],
            "trainee_ids": [trainee_id],
        },
        headers=admin_headers,
    )
    assert task_resp.status_code == 200, task_resp.text
    task_id = task_resp.json()["id"]
    assert task_resp.json()["training_id"] == training_id
    assert len(task_resp.json()["assignees"]) == 1

    # Listing by training returns exactly this task, and it's HR/Admin only.
    by_training_resp = await client.get(f"/api/hrms/task-assessments/tasks/by-training/{training_id}", headers=admin_headers)
    assert by_training_resp.status_code == 200, by_training_resp.text
    tasks = by_training_resp.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id

    with pytest.raises(UserUnauthorizedException):
        await client.get(f"/api/hrms/task-assessments/tasks/by-training/{training_id}", headers=trainee_headers)

    # The trainee can take it exactly like any other Task Assessment.
    start_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
    assert start_resp.status_code == 200, start_resp.text
    task_question_id = start_resp.json()["questions"][0]["id"]
    correct_option_id = next(o["id"] for o in start_resp.json()["questions"][0]["options"] if o["option_text"] == "4")

    save_resp = await client.put(
        f"/api/hrms/task-assessments/tasks/{task_id}/questions/{task_question_id}/answer",
        json={"selected_option_id": correct_option_id},
        headers=trainee_headers,
    )
    assert save_resp.status_code == 200, save_resp.text

    submit_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
    assert submit_resp.status_code == 200, submit_resp.text
    assert submit_resp.json()["percentage"] == 100.0


async def test_trainer_given_assessment_flow_unaffected(client, hrms_admin_token, hrms_user_factory):
    """The default (TRAINER) flow, including legacy trainings created before this field
    existed, keeps working exactly as before."""
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, trainer_token = await hrms_user_factory("HR-flow Trainer3", "hrflow-trainer3@example.com", 6)
    trainee_id, _ = await hrms_user_factory("HR-flow Trainee3", "hrflow-trainee3@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("HR-flow BU3", "hrflow-bu3@example.com", 7)
    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}

    create_resp = await client.post(
        "/api/hrms/training",
        json={
            "topic": "Trainer-Given Assessment Training",
            "trainer_id": trainer_id,
            "trainee_ids": [trainee_id],
            "bu_head_id": bu_head_id,
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "has_assessment": True,
            # assessment_given_by omitted entirely - should default to TRAINER.
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]
    assert create_resp.json()["assessment_given_by"] == "TRAINER"

    await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)

    give_resp = await client.post(
        f"/api/hrms/training/{training_id}/assessments",
        data={"trainee_id": str(trainee_id), "description": "Normal project review"},
        headers=trainer_headers,
    )
    assert give_resp.status_code == 200, give_resp.text


async def test_hr_flow_certificate_issuance(client, hrms_admin_token, hrms_user_factory):
    import shutil

    from app.hrms.services import file_storage_service

    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, trainer_token = await hrms_user_factory("HR-flow Trainer4", "hrflow-trainer4@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("HR-flow Trainee4", "hrflow-trainee4@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("HR-flow BU4", "hrflow-bu4@example.com", 7)
    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}
    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}

    create_resp = await client.post(
        "/api/hrms/training",
        json={
            "topic": "HR Certificate Flow",
            "trainer_id": trainer_id,
            "trainee_ids": [trainee_id],
            "bu_head_id": bu_head_id,
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "has_assessment": True,
            "assessment_given_by": "HR",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]

    await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)
    await client.post(f"/api/hrms/training/{training_id}/complete", headers=trainer_headers)

    try:
        # Before HR has even given the Task Assessment, issuance is blocked.
        early_cert_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": trainee_id, "recipient_name": "HR-flow Trainee4", "issue_date": "2026-09-06"},
            headers=admin_headers,
        )
        assert early_cert_resp.status_code == 400

        question_id = await _create_bank_with_mcq(client, admin_headers)
        task_resp = await client.post(
            "/api/hrms/task-assessments/tasks",
            json={
                "title": "HR Assessment for cert flow",
                "training_id": training_id,
                "time_limit_minutes": 10,
                "question_ids": [question_id],
                "trainee_ids": [trainee_id],
            },
            headers=admin_headers,
        )
        assert task_resp.status_code == 200, task_resp.text
        task_id = task_resp.json()["id"]

        start_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
        tq = start_resp.json()["questions"][0]
        correct_option_id = next(o["id"] for o in tq["options"] if o["option_text"] == "4")
        await client.put(
            f"/api/hrms/task-assessments/tasks/{task_id}/questions/{tq['id']}/answer",
            json={"selected_option_id": correct_option_id},
            headers=trainee_headers,
        )
        submit_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
        assert submit_resp.json()["passed"] is True

        # Passed now, but no certificate template uploaded yet.
        no_template_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": trainee_id, "recipient_name": "HR-flow Trainee4", "issue_date": "2026-09-06"},
            headers=admin_headers,
        )
        assert no_template_resp.status_code == 400

        from io import BytesIO

        from PIL import Image

        template_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        buf = BytesIO()
        template_img.save(buf, format="PNG")
        template_resp = await client.post(
            "/api/hrms/certificate-template",
            files={"file": ("template.png", buf.getvalue(), "image/png")},
            headers=admin_headers,
        )
        assert template_resp.status_code == 200, template_resp.text

        issue_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": trainee_id, "recipient_name": "HR-flow Trainee4", "issue_date": "2026-09-06"},
            headers=admin_headers,
        )
        assert issue_resp.status_code == 200, issue_resp.text
        assert issue_resp.json()["file_url"] is not None

        # Issuing again for the same trainee is rejected.
        dup_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": trainee_id, "recipient_name": "HR-flow Trainee4", "issue_date": "2026-09-06"},
            headers=admin_headers,
        )
        assert dup_resp.status_code == 400
    finally:
        shutil.rmtree(file_storage_service.training_certificate_dir(training_id), ignore_errors=True)
        shutil.rmtree(file_storage_service.certificate_template_dir(), ignore_errors=True)
