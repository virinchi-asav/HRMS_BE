async def test_delete_user_with_no_references_succeeds(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    user_id, _ = await hrms_user_factory("Deletable User", "deletable-user@example.com", 6)

    resp = await client.delete(f"/api/hrms/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text

    get_resp = await client.get(f"/api/hrms/users/{user_id}", headers=admin_headers)
    assert get_resp.status_code == 404


async def test_delete_user_referenced_as_bu_head_is_rejected_with_clear_message(
    client, hrms_admin_token, hrms_user_factory
):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainer_id, _ = await hrms_user_factory("Delete-Test Trainer", "delete-test-trainer@example.com", 6)
    trainee_id, _ = await hrms_user_factory("Delete-Test Trainee", "delete-test-trainee@example.com", 6)
    bu_head_id, _ = await hrms_user_factory("Delete-Test BU", "delete-test-bu@example.com", 7)

    create_resp = await client.post(
        "/api/hrms/training",
        json={
            "topic": "Delete Blocker Training",
            "trainer_ids": [trainer_id],
            "trainee_ids": [trainee_id],
            "bu_head_id": bu_head_id,
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text

    # Deleting the BU Head is rejected with a clear, itemized 400 - not an unhandled
    # 500 from a raw foreign-key constraint violation.
    delete_resp = await client.delete(f"/api/hrms/users/{bu_head_id}", headers=admin_headers)
    assert delete_resp.status_code == 400, delete_resp.text
    assert "BU Head" in delete_resp.json()["detail"]

    # Deleting the Trainer and Trainee are rejected the same way.
    trainer_delete_resp = await client.delete(f"/api/hrms/users/{trainer_id}", headers=admin_headers)
    assert trainer_delete_resp.status_code == 400
    assert "Trainer" in trainer_delete_resp.json()["detail"]

    trainee_delete_resp = await client.delete(f"/api/hrms/users/{trainee_id}", headers=admin_headers)
    assert trainee_delete_resp.status_code == 400
    assert "Trainee" in trainee_delete_resp.json()["detail"]
