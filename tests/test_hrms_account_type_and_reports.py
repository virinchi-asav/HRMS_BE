from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import UserUnauthorizedException
from app.hrms.models.kms_file_view import KmsFileViewEntity
from app.hrms.models.user import UserEntity as HrmsUserEntity
from app.models.account import AccountEntity
from tests.conftest import HrmsTestSessionLocal, TestSessionLocal


async def test_new_user_defaults_to_bench_account(client, hrms_admin_token):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    resp = await client.post(
        "/api/hrms/users",
        json={"name": "Bench Default User", "email": "bench-default@example.com", "role": 6},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    user = resp.json()
    assert user["kms_department_id"] is None
    assert user["kms_account_id"] is not None

    async with TestSessionLocal() as session:
        result = await session.execute(select(AccountEntity).where(AccountEntity.account_name == "Bench"))
        bench = result.scalar_one()
    assert user["kms_account_id"] == bench.account_id


async def test_bank_account_type_and_other_validation(client, hrms_admin_token, seed_lookups):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    account_id = seed_lookups["account_id"]

    # Both account_id and custom_account_type at once is rejected.
    both_resp = await client.post(
        "/api/hrms/task-assessments/banks",
        json={"name": "Bad Bank", "account_id": account_id, "custom_account_type": "Something"},
        headers=admin_headers,
    )
    assert both_resp.status_code == 400

    # "Other" custom_account_type alone succeeds.
    other_resp = await client.post(
        "/api/hrms/task-assessments/banks",
        json={"name": "Other Bank", "custom_account_type": "New Client XYZ"},
        headers=admin_headers,
    )
    assert other_resp.status_code == 200, other_resp.text
    assert other_resp.json()["custom_account_type"] == "New Client XYZ"
    assert other_resp.json()["account_id"] is None

    # An existing account_id alone succeeds and resolves account_name.
    acme_resp = await client.post(
        "/api/hrms/task-assessments/banks",
        json={"name": "Acme Bank", "account_id": account_id},
        headers=admin_headers,
    )
    assert acme_resp.status_code == 200, acme_resp.text
    assert acme_resp.json()["account_id"] == account_id
    assert acme_resp.json()["account_name"] == "Acme"

    # Listing filtered by account_id only returns the matching bank.
    list_resp = await client.get(
        "/api/hrms/task-assessments/banks", params={"account_id": account_id}, headers=admin_headers
    )
    assert list_resp.status_code == 200, list_resp.text
    names = {b["name"] for b in list_resp.json()["content"]}
    assert "Acme Bank" in names
    assert "Other Bank" not in names


async def test_training_report_counts_and_role_gating(client, hrms_admin_token, hrms_user_factory, seed_lookups):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    account_id = seed_lookups["account_id"]
    department_id = seed_lookups["department_id"]

    async with TestSessionLocal() as session:
        account = await session.get(AccountEntity, account_id)
        account.department_id = department_id
        await session.commit()

    trainer_id, trainer_token = await hrms_user_factory("Report Trainer", "report-trainer@example.com", 6)
    trainee_id, _ = await hrms_user_factory("Report Trainee", "report-trainee@example.com", 6)
    bu_head_id, _ = await hrms_user_factory("Report BU", "report-bu@example.com", 7)

    today_str = date.today().isoformat()
    create_resp = await client.post(
        "/api/hrms/training",
        json={
            "topic": "Report Test Training",
            "account_id": account_id,
            "trainer_ids": [trainer_id],
            "trainee_ids": [trainee_id],
            "bu_head_id": bu_head_id,
            "start_date": today_str,
            "end_date": today_str,
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text

    # A Team Member (not Admin/HR) cannot view reports.
    with pytest.raises(UserUnauthorizedException):
        await client.get("/api/hrms/reports/trainings", headers={"Authorization": f"Bearer {trainer_token}"})

    report_resp = await client.get("/api/hrms/reports/trainings", params={"months": 3}, headers=admin_headers)
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()
    assert report["months"] == 3
    assert report["training_programs"]["total"] >= 1
    account_row = next(a for a in report["training_programs"]["by_account"] if a["account_id"] == account_id)
    assert account_row["account_name"] == "Acme"
    assert account_row["department_name"] == "Engineering"
    assert account_row["count"] >= 1

    # Filtering to a different account excludes this training.
    filtered_resp = await client.get(
        "/api/hrms/reports/trainings", params={"months": 3, "account_ids": [account_id + 999]}, headers=admin_headers
    )
    assert filtered_resp.status_code == 200, filtered_resp.text
    assert all(a["account_id"] != account_id for a in filtered_resp.json()["training_programs"]["by_account"])


async def test_user_list_filters_by_account_id(client, hrms_admin_token, hrms_user_factory, seed_lookups):
    """The Task Assessment trainee picker relies on this filter to only show trainees
    under a chosen Account Type."""
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    account_id = seed_lookups["account_id"]

    matching_id, _ = await hrms_user_factory("Acme Trainee", "acme-trainee@example.com", 6)
    other_id, _ = await hrms_user_factory("Other Trainee", "other-trainee-acct@example.com", 6)

    async with HrmsTestSessionLocal() as session:
        user = await session.get(HrmsUserEntity, matching_id)
        user.kms_account_id = account_id
        await session.commit()

    resp = await client.get("/api/hrms/users", params={"account_id": account_id, "size": 100}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    ids = {u["id"] for u in resp.json()["content"]}
    assert matching_id in ids
    assert other_id not in ids


async def test_kms_usage_report(client, hrms_admin_token, hrms_user_factory, seed_lookups):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    account_id = seed_lookups["account_id"]

    active_id, active_token = await hrms_user_factory("KMS Active User", "kms-active@example.com", 6)
    quiet_id, quiet_token = await hrms_user_factory("KMS Quiet User", "kms-quiet@example.com", 6)
    other_account_id, other_account_token = await hrms_user_factory("KMS Other Account", "kms-other-account@example.com", 6)

    async with HrmsTestSessionLocal() as session:
        active_user = await session.get(HrmsUserEntity, active_id)
        active_user.kms_account_id = account_id
        quiet_user = await session.get(HrmsUserEntity, quiet_id)
        quiet_user.kms_account_id = account_id
        await session.commit()

    active_headers = {"Authorization": f"Bearer {active_token}"}
    quiet_headers = {"Authorization": f"Bearer {quiet_token}"}
    other_account_headers = {"Authorization": f"Bearer {other_account_token}"}

    # A Team Member can record views (any authenticated, KMS-mapped user can) - a
    # regular file "open" isn't a privileged action.
    for _ in range(3):
        resp = await client.post("/api/lms/files/101/view", headers=active_headers)
        assert resp.status_code == 200, resp.text
    await client.post("/api/lms/files/102/view", headers=other_account_headers)

    # Backdate one of quiet_user's views to 60 days ago, outside the default window -
    # exercises the date-range filter (can't control viewed_at via the API itself).
    quiet_view_resp = await client.post("/api/lms/files/103/view", headers=quiet_headers)
    assert quiet_view_resp.status_code == 200, quiet_view_resp.text
    async with HrmsTestSessionLocal() as session:
        result = await session.execute(select(KmsFileViewEntity).where(KmsFileViewEntity.user_id == quiet_id))
        view = result.scalar_one()
        view.viewed_at = datetime.utcnow() - timedelta(days=60)
        await session.commit()

    # A Team Member cannot see the report itself (Admin/HR only, same as /trainings).
    with pytest.raises(UserUnauthorizedException):
        await client.get("/api/hrms/reports/kms-usage", headers=active_headers)

    # Default (last 30 days): active_user shows up with 3 views, quiet_user's lone view
    # is outside the window and excluded entirely, other_account_id shows under no
    # account filter.
    report_resp = await client.get("/api/hrms/reports/kms-usage", headers=admin_headers)
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()
    users_by_id = {u["user_id"]: u for u in report["users"]}
    assert users_by_id[active_id]["view_count"] == 3
    assert users_by_id[active_id]["account_name"] == "Acme"
    assert quiet_id not in users_by_id
    assert other_account_id in users_by_id
    assert users_by_id[other_account_id]["account_name"] == "Unspecified"

    # Filtering to the seeded account excludes the user with no account set.
    filtered_resp = await client.get(
        "/api/hrms/reports/kms-usage", params={"account_id": account_id}, headers=admin_headers
    )
    assert filtered_resp.status_code == 200, filtered_resp.text
    filtered = filtered_resp.json()
    assert {u["user_id"] for u in filtered["users"]} == {active_id}
    assert filtered["total_active_users"] == 1
    assert filtered["total_views"] == 3
    account_row = next(a for a in filtered["by_account"] if a["account_id"] == account_id)
    assert account_row["user_count"] == 1
    assert account_row["view_count"] == 3

    # A wider custom range picks the backdated view back up.
    wide_resp = await client.get(
        "/api/hrms/reports/kms-usage",
        params={"start_date": (date.today() - timedelta(days=90)).isoformat(), "end_date": date.today().isoformat()},
        headers=admin_headers,
    )
    assert wide_resp.status_code == 200, wide_resp.text
    wide_users = {u["user_id"]: u for u in wide_resp.json()["users"]}
    assert quiet_id in wide_users
    assert wide_users[quiet_id]["view_count"] == 1
