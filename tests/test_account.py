async def test_account_endpoints_require_auth(client):
    response = await client.get("/api/lms/account/accounts")
    assert response.status_code == 401


async def test_add_and_fetch_account(client, auth_token, seed_lookups):
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {
        "accountName": "NewAccount",
        "accountDescription": "desc",
        "departmentId": seed_lookups["department_id"],
    }
    response = await client.post("/api/lms/account/add", json=payload, headers=headers)
    assert response.status_code == 200, response.text

    response = await client.get("/api/lms/account/NewAccount", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["accountName"] == "NewAccount"


async def test_add_duplicate_account_rejected(client, auth_token, seed_lookups):
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {
        "accountName": "DupAccount",
        "accountDescription": "desc",
        "departmentId": seed_lookups["department_id"],
    }
    first = await client.post("/api/lms/account/add", json=payload, headers=headers)
    assert first.status_code == 200

    second = await client.post("/api/lms/account/add", json=payload, headers=headers)
    assert second.status_code == 400
    assert second.json()["message"] == "Account name already exist!"


async def test_list_accounts_excludes_sentinel(client, auth_token, seed_lookups):
    headers = {"Authorization": f"Bearer {auth_token}"}
    # The seeded "Acme" account (id != 0) should show up in the paginated list.
    response = await client.get("/api/lms/account/accounts", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    names = [a["accountName"] for a in body["content"]]
    assert "Acme" in names
