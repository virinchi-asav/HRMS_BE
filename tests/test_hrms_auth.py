async def test_login_success(hrms_admin_token):
    assert hrms_admin_token


async def test_login_wrong_password(client, hrms_admin_token):
    response = await client.post(
        "/api/hrms/auth/login", json={"email": "hrms-admin@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


async def test_me_requires_auth(client):
    response = await client.get("/api/hrms/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    response = await client.get("/api/hrms/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "hrms-admin@example.com"


async def test_change_password(client, hrms_admin_token):
    headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    response = await client.patch(
        "/api/hrms/auth/change-password",
        headers=headers,
        json={"current_password": "password123", "password": "newpass123", "password_confirm": "newpass123"},
    )
    assert response.status_code == 200, response.text

    # old password no longer works
    stale = await client.post(
        "/api/hrms/auth/login", json={"email": "hrms-admin@example.com", "password": "password123"}
    )
    assert stale.status_code == 401

    fresh = await client.post(
        "/api/hrms/auth/login", json={"email": "hrms-admin@example.com", "password": "newpass123"}
    )
    assert fresh.status_code == 200
