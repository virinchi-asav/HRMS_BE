from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import UserUnauthorizedException
from app.hrms.models.task_assessment import TaskAssigneeEntity
from tests.conftest import HrmsTestSessionLocal


async def _create_bank_with_questions(client, headers):
    bank_resp = await client.post("/api/hrms/task-assessments/banks", json={"name": "Python Basics"}, headers=headers)
    assert bank_resp.status_code == 200, bank_resp.text
    bank_id = bank_resp.json()["id"]

    mcq_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "Python",
            "question_type": "MULTIPLE_CHOICE",
            "question_text": "Which is a Python keyword?",
            "marks": 2,
            "options": [
                {"option_text": "def", "is_correct": True},
                {"option_text": "func", "is_correct": False},
            ],
        },
        headers=headers,
    )
    assert mcq_resp.status_code == 200, mcq_resp.text

    tf_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "Python",
            "question_type": "TRUE_FALSE",
            "question_text": "Python is dynamically typed.",
            "correct_answer_text": "True",
        },
        headers=headers,
    )
    assert tf_resp.status_code == 200, tf_resp.text

    fib_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "Python",
            "question_type": "FILL_IN_BLANK",
            "question_text": "The ___ keyword defines a function.",
            "correct_answer_text": "def",
        },
        headers=headers,
    )
    assert fib_resp.status_code == 200, fib_resp.text

    ea_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "Python",
            "question_type": "ENTER_ANSWER",
            "question_text": "Who created Python?",
            "correct_answer_text": "Guido van Rossum",
        },
        headers=headers,
    )
    assert ea_resp.status_code == 200, ea_resp.text

    return bank_id, {"mcq": mcq_resp.json(), "tf": tf_resp.json(), "fib": fib_resp.json(), "ea": ea_resp.json()}


async def test_task_assessments_requires_auth(client):
    response = await client.get("/api/hrms/task-assessments/tasks")
    assert response.status_code == 401


async def test_bank_question_validators(client, hrms_admin_token):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    bank_resp = await client.post("/api/hrms/task-assessments/banks", json={"name": "Validator Bank"}, headers=admin_headers)
    bank_id = bank_resp.json()["id"]

    # MCQ with zero correct options is rejected.
    resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "M",
            "question_type": "MULTIPLE_CHOICE",
            "question_text": "Q?",
            "options": [{"option_text": "A", "is_correct": False}, {"option_text": "B", "is_correct": False}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400

    # MCQ with two correct options is rejected.
    resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "M",
            "question_type": "MULTIPLE_CHOICE",
            "question_text": "Q?",
            "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B", "is_correct": True}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400

    # Non-MCQ missing correct_answer_text is rejected.
    resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={"module_name": "M", "question_type": "TRUE_FALSE", "question_text": "Q?"},
        headers=admin_headers,
    )
    assert resp.status_code == 400

    # A valid MCQ question succeeds.
    resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions",
        json={
            "module_name": "M",
            "question_type": "MULTIPLE_CHOICE",
            "question_text": "Q?",
            "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B", "is_correct": False}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text


async def test_bank_and_task_creation_require_hr_or_admin(client, hrms_admin_token, hrms_user_factory):
    """Question banks and Tasks are both authored by HR/Admin only - a plain
    TEAM_MEMBER (whether acting as a Trainer or Trainee) has no create/manage access to
    either, only the trainee-facing take/report-of-their-own-result flow."""
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    _, team_member_token = await hrms_user_factory("Team Member One", "team-member-ta1@example.com", 6)
    trainee_id, _ = await hrms_user_factory("Trainee One", "trainee-ta1@example.com", 6)
    team_member_headers = {"Authorization": f"Bearer {team_member_token}"}

    bank_id, questions = await _create_bank_with_questions(client, admin_headers)
    question_ids = [questions["mcq"]["id"]]

    # require_role rejections raise rather than returning a 403 response (a pre-existing
    # app-wide behavior, not something introduced here) - httpx's ASGITransport
    # re-raises them in-process during tests.
    with pytest.raises(UserUnauthorizedException):
        await client.post("/api/hrms/task-assessments/banks", json={"name": "Should Fail"}, headers=team_member_headers)
    with pytest.raises(UserUnauthorizedException):
        await client.get("/api/hrms/task-assessments/banks", headers=team_member_headers)
    with pytest.raises(UserUnauthorizedException):
        await client.post(
            f"/api/hrms/task-assessments/banks/{bank_id}/questions",
            json={"module_name": "M", "question_type": "ENTER_ANSWER", "question_text": "Q?", "correct_answer_text": "A"},
            headers=team_member_headers,
        )
    with pytest.raises(UserUnauthorizedException):
        await client.post(
            "/api/hrms/task-assessments/tasks",
            json={"title": "Python Quiz", "time_limit_minutes": 10, "question_ids": question_ids},
            headers=team_member_headers,
        )

    # HR/Admin can create a task, with or without assigning trainees up front.
    resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={"title": "Python Quiz", "time_limit_minutes": 10, "question_ids": question_ids},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["id"]
    assert resp.json()["assignees"] == []

    assign_resp = await client.post(
        f"/api/hrms/task-assessments/tasks/{task_id}/assign", json={"trainee_ids": [trainee_id]}, headers=admin_headers
    )
    assert assign_resp.status_code == 200, assign_resp.text
    assignees = assign_resp.json()["assignees"]
    assert len(assignees) == 1
    assert assignees[0]["trainee_id"] == trainee_id
    assert assignees[0]["status"] == "NOT_STARTED"


async def test_full_take_and_grade_flow(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainee_id, trainee_token = await hrms_user_factory("Trainee Two", "trainee-ta2@example.com", 6)
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}

    bank_id, questions = await _create_bank_with_questions(client, admin_headers)
    question_ids = [questions["mcq"]["id"], questions["tf"]["id"], questions["fib"]["id"], questions["ea"]["id"]]

    create_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Python Quiz",
            "time_limit_minutes": 30,
            "pass_percentage": 50,
            "question_ids": question_ids,
            "trainee_ids": [trainee_id],
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    task_id = create_resp.json()["id"]
    assert create_resp.json()["total_marks"] == 5  # 2 (MCQ) + 1 + 1 + 1

    start_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
    assert start_resp.status_code == 200, start_resp.text
    take = start_resp.json()
    assert take["deadline_at"] is not None
    # The trainee-facing take view must never leak correctness/answer keys.
    assert "is_correct" not in start_resp.text
    assert "correct_answer_text" not in start_resp.text

    tq_by_type = {q["question_type"]: q for q in take["questions"]}
    mcq_tq = tq_by_type["MULTIPLE_CHOICE"]
    correct_option_id = next(o["id"] for o in mcq_tq["options"] if o["option_text"] == "def")

    async def _answer(tq_id, **kwargs):
        resp = await client.put(
            f"/api/hrms/task-assessments/tasks/{task_id}/questions/{tq_id}/answer", json=kwargs, headers=trainee_headers
        )
        assert resp.status_code == 200, resp.text

    await _answer(mcq_tq["id"], selected_option_id=correct_option_id)
    await _answer(tq_by_type["TRUE_FALSE"]["id"], answer_text="True")
    await _answer(tq_by_type["FILL_IN_BLANK"]["id"], answer_text="def")
    await _answer(tq_by_type["ENTER_ANSWER"]["id"], answer_text="  guido van rossum  ")  # case/whitespace-insensitive

    submit_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
    assert submit_resp.status_code == 200, submit_resp.text
    result = submit_resp.json()
    assert result["status"] == "SUBMITTED"
    assert result["marks_obtained"] == 5
    assert result["total_marks"] == 5
    assert result["percentage"] == 100.0
    assert result["passed"] is True

    # Resubmitting is idempotent - same result, no error.
    resubmit_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
    assert resubmit_resp.status_code == 200, resubmit_resp.text
    assert resubmit_resp.json() == result

    report_resp = await client.get(f"/api/hrms/task-assessments/tasks/{task_id}/report", headers=admin_headers)
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()
    assert report["submitted_count"] == 1
    assert report["pass_count"] == 1
    assert report["average_percentage"] == 100.0
    assert report["rows"][0]["trainee_id"] == trainee_id
    assert report["rows"][0]["status"] == "SUBMITTED"


async def test_timeout_auto_finalizes(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainee_id, trainee_token = await hrms_user_factory("Trainee Three", "trainee-ta3@example.com", 6)
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}

    bank_id, questions = await _create_bank_with_questions(client, admin_headers)
    create_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Timed Quiz",
            "time_limit_minutes": 10,
            "question_ids": [questions["mcq"]["id"]],
            "trainee_ids": [trainee_id],
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    task_id = create_resp.json()["id"]
    task_question_id = create_resp.json()["questions"][0]["id"]

    start_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
    assert start_resp.status_code == 200, start_resp.text

    # Simulate the deadline having already passed - this backend deliberately has no
    # scheduler, so the server-side safety net only fires lazily on the next touch.
    async with HrmsTestSessionLocal() as session:
        result = await session.execute(
            select(TaskAssigneeEntity).where(TaskAssigneeEntity.task_id == task_id, TaskAssigneeEntity.trainee_id == trainee_id)
        )
        assignee = result.scalar_one()
        assignee.deadline_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    # Saving an answer after the deadline is rejected...
    save_resp = await client.put(
        f"/api/hrms/task-assessments/tasks/{task_id}/questions/{task_question_id}/answer",
        json={"selected_option_id": None},
        headers=trainee_headers,
    )
    assert save_resp.status_code == 400

    # ...and the report reflects the auto-submit even though the trainee never
    # explicitly submitted, because the report endpoint finalizes every row it reads.
    report_resp = await client.get(f"/api/hrms/task-assessments/tasks/{task_id}/report", headers=admin_headers)
    assert report_resp.status_code == 200, report_resp.text
    row = report_resp.json()["rows"][0]
    assert row["status"] == "AUTO_SUBMITTED"
    assert row["submitted_at"] is not None
    assert row["marks_obtained"] == 0  # never answered anything before time ran out


async def _create_bank_with_n_true_false_questions(client, headers, n, name="Big Bank"):
    bank_resp = await client.post("/api/hrms/task-assessments/banks", json={"name": name}, headers=headers)
    assert bank_resp.status_code == 200, bank_resp.text
    bank_id = bank_resp.json()["id"]
    for i in range(n):
        resp = await client.post(
            f"/api/hrms/task-assessments/banks/{bank_id}/questions",
            json={
                "module_name": "General",
                "question_type": "TRUE_FALSE",
                "question_text": f"Statement number {i} is true.",
                "correct_answer_text": "True",
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
    return bank_id


async def test_retry_lockout_and_hr_reassign_flow(client, hrms_admin_token, hrms_user_factory):
    """3-strikes (here 2, to keep the test short) flow: a failed attempt lets the
    trainee self-retry; once every attempt is used up they're locked_out and only HR's
    reassign endpoint (not another retry) can grant a fresh cycle."""
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainee_id, trainee_token = await hrms_user_factory("Trainee Retry", "trainee-retry@example.com", 6)
    trainee_headers = {"Authorization": f"Bearer {trainee_token}"}

    bank_id, questions = await _create_bank_with_questions(client, admin_headers)
    mcq = questions["mcq"]

    create_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Retry Quiz",
            "time_limit_minutes": 10,
            "pass_percentage": 90,
            "max_attempts": 2,
            "question_ids": [mcq["id"]],
            "trainee_ids": [trainee_id],
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    task_id = create_resp.json()["id"]
    assignee = create_resp.json()["assignees"][0]
    assert assignee["attempt_number"] == 1
    assert assignee["max_attempts"] == 2

    # Reassign is only for a locked-out trainee - refused while still on attempt 1.
    early_reassign = await client.post(
        f"/api/hrms/task-assessments/tasks/{task_id}/assignees/{trainee_id}/reassign", headers=admin_headers
    )
    assert early_reassign.status_code == 400

    # Attempt 1: never answer, submit -> fails (0% < 90% pass mark), can retry.
    start_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
    assert start_resp.status_code == 200, start_resp.text
    assert start_resp.json()["attempt_number"] == 1
    assert start_resp.json()["max_attempts"] == 2

    submit_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
    assert submit_resp.status_code == 200, submit_resp.text
    result = submit_resp.json()
    assert result["passed"] is False
    assert result["attempt_number"] == 1
    assert result["can_retry"] is True
    assert result["locked_out"] is False

    # A trainee can self-retry - no HR involvement needed while attempts remain.
    retry_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/retry", headers=trainee_headers)
    assert retry_resp.status_code == 200, retry_resp.text
    assert retry_resp.json() == {"attempt_number": 2, "max_attempts": 2, "status": "NOT_STARTED"}

    # Attempt 2 (the last one): fail again -> now locked_out, not can_retry.
    await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
    submit_resp2 = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
    assert submit_resp2.status_code == 200, submit_resp2.text
    result2 = submit_resp2.json()
    assert result2["attempt_number"] == 2
    assert result2["can_retry"] is False
    assert result2["locked_out"] is True

    # No more self-retries once locked out.
    retry_again = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/retry", headers=trainee_headers)
    assert retry_again.status_code == 400

    # HR sees the lockout in the report.
    report_resp = await client.get(f"/api/hrms/task-assessments/tasks/{task_id}/report", headers=admin_headers)
    assert report_resp.status_code == 200, report_resp.text
    row = report_resp.json()["rows"][0]
    assert row["attempt_number"] == 2
    assert row["max_attempts"] == 2
    assert row["locked_out"] is True

    # HR reassigns - grants a fresh cycle (max_attempts bumped by another +2) without
    # resetting attempt_number, which keeps climbing monotonically.
    reassign_resp = await client.post(
        f"/api/hrms/task-assessments/tasks/{task_id}/assignees/{trainee_id}/reassign", headers=admin_headers
    )
    assert reassign_resp.status_code == 200, reassign_resp.text
    reassigned = next(a for a in reassign_resp.json()["assignees"] if a["trainee_id"] == trainee_id)
    assert reassigned["attempt_number"] == 3
    assert reassigned["max_attempts"] == 4
    assert reassigned["status"] == "NOT_STARTED"
    assert reassigned["locked_out"] is False

    # Reassigning again immediately is refused - the trainee isn't locked out anymore.
    second_reassign = await client.post(
        f"/api/hrms/task-assessments/tasks/{task_id}/assignees/{trainee_id}/reassign", headers=admin_headers
    )
    assert second_reassign.status_code == 400

    # Attempt 3, answered correctly this time, passes.
    start3 = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee_headers)
    take3 = start3.json()
    assert take3["attempt_number"] == 3
    correct_option_id = next(o["id"] for o in take3["questions"][0]["options"] if o["option_text"] == "def")
    await client.put(
        f"/api/hrms/task-assessments/tasks/{task_id}/questions/{take3['questions'][0]['id']}/answer",
        json={"selected_option_id": correct_option_id},
        headers=trainee_headers,
    )
    final_submit = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee_headers)
    assert final_submit.status_code == 200, final_submit.text
    assert final_submit.json()["passed"] is True
    assert final_submit.json()["can_retry"] is False
    assert final_submit.json()["locked_out"] is False


async def test_random_question_mode(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    trainee1_id, trainee1_token = await hrms_user_factory("Trainee Random One", "trainee-random1@example.com", 6)
    trainee2_id, _ = await hrms_user_factory("Trainee Random Two", "trainee-random2@example.com", 6)
    trainee1_headers = {"Authorization": f"Bearer {trainee1_token}"}

    small_bank_id, _ = await _create_bank_with_questions(client, admin_headers)  # only 4 questions
    big_bank_id = await _create_bank_with_n_true_false_questions(client, admin_headers, 12)

    # Requesting more than the bank has active questions for is rejected up front.
    too_small_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Too Big a Draw",
            "time_limit_minutes": 10,
            "question_mode": "RANDOM",
            "source_bank_id": small_bank_id,
            "random_question_count": 10,
        },
        headers=admin_headers,
    )
    assert too_small_resp.status_code == 400

    # random_question_count must be one of the fixed allowed sizes.
    bad_count_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Bad Count",
            "time_limit_minutes": 10,
            "question_mode": "RANDOM",
            "source_bank_id": big_bank_id,
            "random_question_count": 12,
        },
        headers=admin_headers,
    )
    assert bad_count_resp.status_code == 400

    # question_ids must be empty in RANDOM mode.
    mixed_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Mixed Mode",
            "time_limit_minutes": 10,
            "question_mode": "RANDOM",
            "source_bank_id": big_bank_id,
            "random_question_count": 10,
            "question_ids": [1],
        },
        headers=admin_headers,
    )
    assert mixed_resp.status_code == 400

    create_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={
            "title": "Random Draw Quiz",
            "time_limit_minutes": 10,
            "question_mode": "RANDOM",
            "source_bank_id": big_bank_id,
            "random_question_count": 10,
            "trainee_ids": [trainee1_id, trainee2_id],
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    task = create_resp.json()
    task_id = task["id"]
    assert task["question_mode"] == "RANDOM"
    assert task["source_bank_id"] == big_bank_id
    assert task["random_question_count"] == 10
    # A RANDOM-mode task has no single shared question set at the management level -
    # each assignee draws their own the first time they start.
    assert task["questions"] == []
    assert task["total_marks"] == 0

    start_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/start", headers=trainee1_headers)
    assert start_resp.status_code == 200, start_resp.text
    take = start_resp.json()
    assert len(take["questions"]) == 10
    assert take["attempt_number"] == 1
    assert take["max_attempts"] == 3  # default

    # Grading is scoped to this trainee's own drawn questions (10 x 1 mark each).
    submit_resp = await client.post(f"/api/hrms/task-assessments/tasks/{task_id}/submit", headers=trainee1_headers)
    assert submit_resp.status_code == 200, submit_resp.text
    result = submit_resp.json()
    assert result["total_marks"] == 10
    assert result["marks_obtained"] == 0  # nothing answered


async def test_report_requires_ownership(client, hrms_admin_token, hrms_user_factory):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}
    _, other_team_member_token = await hrms_user_factory("Team Member Five", "team-member-ta5@example.com", 6)
    other_headers = {"Authorization": f"Bearer {other_team_member_token}"}

    bank_id, questions = await _create_bank_with_questions(client, admin_headers)
    create_resp = await client.post(
        "/api/hrms/task-assessments/tasks",
        json={"title": "Owned Quiz", "time_limit_minutes": 10, "question_ids": [questions["mcq"]["id"]]},
        headers=admin_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    task_id = create_resp.json()["id"]

    # A plain TEAM_MEMBER (not assigned, not Admin/HR) cannot view the report - the
    # route itself stays open to any TASK_ROLES caller (trainees need it too, via other
    # endpoints), so ownership is enforced in the service layer as a 404.
    resp = await client.get(f"/api/hrms/task-assessments/tasks/{task_id}/report", headers=other_headers)
    assert resp.status_code == 404

    # The creator (HR/Admin) can.
    own_resp = await client.get(f"/api/hrms/task-assessments/tasks/{task_id}/report", headers=admin_headers)
    assert own_resp.status_code == 200


async def test_bulk_question_import_from_downloaded_template(client, hrms_admin_token):
    admin_headers = {"Authorization": f"Bearer {hrms_admin_token}"}

    template_resp = await client.get("/api/hrms/task-assessments/questions/template", headers=admin_headers)
    assert template_resp.status_code == 200, template_resp.text
    assert template_resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    bank_resp = await client.post(
        "/api/hrms/task-assessments/banks", json={"name": "Bulk Import Bank"}, headers=admin_headers
    )
    assert bank_resp.status_code == 200, bank_resp.text
    bank_id = bank_resp.json()["id"]

    # Uploading the template unmodified should create exactly its 4 example rows (one of
    # each question type) with no errors - this is the "download, fill in, upload" flow.
    import_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions/import",
        headers=admin_headers,
        files={
            "file": (
                "question_bank_template.xlsx",
                template_resp.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert import_resp.status_code == 200, import_resp.text
    result = import_resp.json()
    assert result["created"] == 4
    assert result["errors"] == []

    list_resp = await client.get(f"/api/hrms/task-assessments/banks/{bank_id}/questions", headers=admin_headers)
    assert list_resp.status_code == 200, list_resp.text
    imported = {q["question_type"]: q for q in list_resp.json()["content"]}
    assert set(imported) == {"MULTIPLE_CHOICE", "TRUE_FALSE", "FILL_IN_BLANK", "ENTER_ANSWER"}
    mcq = imported["MULTIPLE_CHOICE"]
    assert len(mcq["options"]) == 4
    assert sum(1 for o in mcq["options"] if o["is_correct"]) == 1

    # A CSV with a good row and a bad one (unknown question_type) reports both a created
    # count and a per-row error, rather than failing the whole upload.
    csv_content = (
        b"module_name,question_type,question_text,marks,correct_answer_text\n"
        b"Extra,TRUE_FALSE,Is water wet?,1,True\n"
        b"Extra,NOT_A_TYPE,Bogus row,1,x\n"
    )
    csv_import_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions/import",
        headers=admin_headers,
        files={"file": ("more_questions.csv", csv_content, "text/csv")},
    )
    assert csv_import_resp.status_code == 200, csv_import_resp.text
    csv_result = csv_import_resp.json()
    assert csv_result["created"] == 1
    assert len(csv_result["errors"]) == 1
    assert csv_result["errors"][0]["row"] == 3

    # Missing required columns is reported as a single file-level error, not a crash.
    bad_resp = await client.post(
        f"/api/hrms/task-assessments/banks/{bank_id}/questions/import",
        headers=admin_headers,
        files={"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")},
    )
    assert bad_resp.status_code == 200, bad_resp.text
    bad_result = bad_resp.json()
    assert bad_result["created"] == 0
    assert "Missing required column" in bad_result["errors"][0]["message"]
