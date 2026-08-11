import shutil

from app.hrms.services import file_storage_service


async def _setup_training(client, admin_headers, hrms_user_factory, has_assessment=True):
    trainer_id, trainer_token = await hrms_user_factory("Trainer AS", "trainer.as@example.com", 6)
    trainee_id, trainee_token = await hrms_user_factory("Trainee AS", "trainee.as@example.com", 6)
    other_trainee_id, other_trainee_token = await hrms_user_factory("Other Trainee AS", "other.as@example.com", 6)
    bu_head_id, bu_head_token = await hrms_user_factory("BU AS", "bu.as@example.com", 7)

    payload = {
        "topic": "Assessment Flow",
        "description": "Testing assessments",
        "trainer_id": trainer_id,
        "trainee_ids": [trainee_id, other_trainee_id],
        "bu_head_id": bu_head_id,
        "start_date": "2026-05-01",
        "end_date": "2026-05-10",
        "has_assessment": has_assessment,
    }
    create_resp = await client.post("/api/hrms/training", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200, create_resp.text
    training_id = create_resp.json()["id"]
    assert create_resp.json()["has_assessment"] == has_assessment

    bu_head_headers = {"Authorization": f"Bearer {bu_head_token}"}
    approve_resp = await client.post(f"/api/hrms/training/{training_id}/approve", headers=bu_head_headers)
    assert approve_resp.status_code == 200, approve_resp.text

    return {
        "training_id": training_id,
        "trainer_headers": {"Authorization": f"Bearer {trainer_token}"},
        "trainee_id": trainee_id,
        "trainee_headers": {"Authorization": f"Bearer {trainee_token}"},
        "other_trainee_id": other_trainee_id,
        "other_trainee_headers": {"Authorization": f"Bearer {other_trainee_token}"},
        "bu_head_headers": bu_head_headers,
    }


async def test_assessment_requires_has_assessment_enabled(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    ctx = await _setup_training(client, admin_headers, hrms_user_factory, has_assessment=False)

    resp = await client.post(
        f"/api/hrms/training/{ctx['training_id']}/assessments",
        data={"trainee_id": ctx["trainee_id"], "description": "Build a small API"},
        headers=ctx["trainer_headers"],
    )
    assert resp.status_code == 400
    assert "assessment" in resp.json()["detail"].lower()


async def test_full_assessment_and_certificate_flow(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    ctx = await _setup_training(client, admin_headers, hrms_user_factory, has_assessment=True)
    training_id = ctx["training_id"]

    try:
        # Trainer gives an assessment to one trainee, with a detail document.
        create_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments",
            data={"trainee_id": ctx["trainee_id"], "description": "Build a small REST API"},
            files={"detail_document": ("brief.txt", b"Assessment brief", "text/plain")},
            headers=ctx["trainer_headers"],
        )
        assert create_resp.status_code == 200, create_resp.text
        assessment = create_resp.json()
        assessment_id = assessment["id"]
        assert assessment["status"] == "PENDING"
        assert assessment["detail_document_url"] is not None

        # The other trainee (no assessment given) can't see or touch this one.
        other_get_resp = await client.get(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}", headers=ctx["other_trainee_headers"]
        )
        assert other_get_resp.status_code == 404

        other_submission_resp = await client.patch(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/submission",
            json={"status": "IN_PROGRESS"},
            headers=ctx["other_trainee_headers"],
        )
        assert other_submission_resp.status_code == 404

        # Trainee moves to In Progress, sets repo URL, uploads screenshots + zip.
        submission_resp = await client.patch(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/submission",
            json={"status": "IN_PROGRESS", "github_repo_url": "https://github.com/example/repo"},
            headers=ctx["trainee_headers"],
        )
        assert submission_resp.status_code == 200, submission_resp.text
        assert submission_resp.json()["status"] == "IN_PROGRESS"

        screenshots_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/screenshots",
            files=[
                ("files", ("s1.png", b"fakepngbytes1", "image/png")),
                ("files", ("s2.png", b"fakepngbytes2", "image/png")),
            ],
            headers=ctx["trainee_headers"],
        )
        assert screenshots_resp.status_code == 200, screenshots_resp.text
        assert len(screenshots_resp.json()["screenshots"]) == 2

        zip_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/zip",
            files={"file": ("project.zip", b"fakezipbytes", "application/zip")},
            headers=ctx["trainee_headers"],
        )
        assert zip_resp.status_code == 200, zip_resp.text
        assert zip_resp.json()["project_zip_url"] is not None

        # Trainee marks it Ready for Review.
        ready_resp = await client.patch(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/submission",
            json={"status": "READY_FOR_REVIEW"},
            headers=ctx["trainee_headers"],
        )
        assert ready_resp.status_code == 200
        assert ready_resp.json()["status"] == "READY_FOR_REVIEW"

        # Trainee can no longer edit their own submission once Ready for Review... actually
        # review hasn't happened yet, only Success/Failure is terminal - re-editing before
        # review is still allowed via status, but let's confirm the BU Head (not the trainer)
        # cannot review it.
        bu_review_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/review",
            json={"marks": 90, "status": "SUCCESS"},
            headers=ctx["bu_head_headers"],
        )
        assert bu_review_resp.status_code == 404

        # Trainer reviews and marks Success.
        review_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/review",
            json={"marks": 92, "status": "SUCCESS"},
            headers=ctx["trainer_headers"],
        )
        assert review_resp.status_code == 200, review_resp.text
        assert review_resp.json()["status"] == "SUCCESS"
        assert review_resp.json()["marks"] == 92

        # Trainee can no longer update their submission once reviewed.
        post_review_update = await client.patch(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/submission",
            json={"status": "IN_PROGRESS"},
            headers=ctx["trainee_headers"],
        )
        assert post_review_update.status_code == 404

        # Trainer completes the training.
        complete_resp = await client.post(
            f"/api/hrms/training/{training_id}/complete", headers=ctx["trainer_headers"]
        )
        assert complete_resp.status_code == 200, complete_resp.text

        # No certificate template yet - issuance should fail.
        no_template_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": ctx["trainee_id"], "recipient_name": "Trainee AS", "issue_date": "2026-05-11"},
            headers=admin_headers,
        )
        assert no_template_resp.status_code == 400

        # Admin uploads a real (tiny) certificate template image.
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
        assert template_resp.json()["file_url"] is not None

        # Now issuance succeeds.
        issue_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": ctx["trainee_id"], "recipient_name": "Trainee AS", "issue_date": "2026-05-11"},
            headers=admin_headers,
        )
        assert issue_resp.status_code == 200, issue_resp.text
        certificate = issue_resp.json()
        assert certificate["file_url"] is not None

        # The Trainee can see their own certificate.
        list_resp = await client.get(
            f"/api/hrms/training/{training_id}/certificates", headers=ctx["trainee_headers"]
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # Issuing again for the same trainee is rejected (already issued).
        dup_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={"trainee_id": ctx["trainee_id"], "recipient_name": "Trainee AS", "issue_date": "2026-05-11"},
            headers=admin_headers,
        )
        assert dup_resp.status_code == 400

        # The other trainee never got an assessment marked Success - issuance blocked.
        other_issue_resp = await client.post(
            f"/api/hrms/training/{training_id}/certificates",
            json={
                "trainee_id": ctx["other_trainee_id"],
                "recipient_name": "Other Trainee AS",
                "issue_date": "2026-05-11",
            },
            headers=admin_headers,
        )
        assert other_issue_resp.status_code == 400
    finally:
        shutil.rmtree(file_storage_service.training_assessment_dir(training_id, 0).parent, ignore_errors=True)
        shutil.rmtree(file_storage_service.training_certificate_dir(training_id), ignore_errors=True)
        shutil.rmtree(file_storage_service.certificate_template_dir(), ignore_errors=True)


async def test_review_rejected_unless_ready_for_review(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    ctx = await _setup_training(client, admin_headers, hrms_user_factory, has_assessment=True)
    training_id = ctx["training_id"]

    try:
        create_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments",
            data={"trainee_id": ctx["trainee_id"], "description": "Write unit tests"},
            headers=ctx["trainer_headers"],
        )
        assessment_id = create_resp.json()["id"]

        # Still PENDING - review should be rejected.
        review_resp = await client.post(
            f"/api/hrms/training/{training_id}/assessments/{assessment_id}/review",
            json={"marks": 50, "status": "FAILURE"},
            headers=ctx["trainer_headers"],
        )
        assert review_resp.status_code == 404
    finally:
        shutil.rmtree(file_storage_service.training_assessment_dir(training_id, 0).parent, ignore_errors=True)
