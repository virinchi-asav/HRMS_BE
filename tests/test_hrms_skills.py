async def test_create_and_edit_own_skill(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    payload = {
        "skill_name": "Python",
        "skill_category": "Programming",
        "rating": "4",
        "level_of_proficiency": "80",
        "account": "Internal",
        "sub_skills": [
            {"sub_skill_name": "FastAPI", "sub_skill_category": "Framework", "rating": "3"},
        ],
    }
    create_resp = await client.post("/api/hrms/skills", json=payload, headers=headers)
    assert create_resp.status_code == 200, create_resp.text
    skill = create_resp.json()
    assert skill["skill_name"] == "Python"
    assert len(skill["sub_skills"]) == 1
    assert skill["sub_skills"][0]["skill_name"] == "FastAPI"

    skill_id = skill["skill_id"]

    get_resp = await client.get(f"/api/hrms/skills/{skill_id}", headers=headers)
    assert get_resp.status_code == 200

    update_payload = dict(payload)
    update_payload["rating"] = "5"
    update_payload["sub_skills"] = [
        {"id": skill["sub_skills"][0]["id"], "sub_skill_name": "FastAPI", "sub_skill_category": "Framework", "rating": "4"},
    ]
    update_resp = await client.put(f"/api/hrms/skills/{skill_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["skill"]["rating"] == "5"

    delete_resp = await client.delete(f"/api/hrms/skills/{skill_id}", headers=headers)
    assert delete_resp.status_code == 200

    get_after_delete = await client.get("/api/hrms/skills", headers=headers)
    assert all(s["skill_id"] != skill_id for s in get_after_delete.json()["page"]["content"])

    restore_resp = await client.post(f"/api/hrms/skills/{skill_id}/restore", headers=headers)
    assert restore_resp.status_code == 200

    get_after_restore = await client.get("/api/hrms/skills", headers=headers)
    assert any(s["skill_id"] == skill_id for s in get_after_restore.json()["page"]["content"])


async def test_skills_require_auth(client):
    response = await client.get("/api/hrms/skills")
    assert response.status_code == 401
