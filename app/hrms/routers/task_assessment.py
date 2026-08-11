from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EXCEL_SHEET_CONTENT_TYPE
from app.core.deps import get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db, require_role
from app.hrms.schemas.task_assessment import (
    AnswerSaveRequest,
    AssignByLocationRequest,
    AssignTraineesRequest,
    BankCreateRequest,
    BankQuestionCreateRequest,
    BankQuestionImportResponse,
    BankQuestionResponse,
    BankQuestionUpdateRequest,
    BankResponse,
    BankUpdateRequest,
    RetryResponse,
    SubmitTaskRequest,
    TaskCreateRequest,
    TaskManageDetailResponse,
    TaskReportResponse,
    TaskResultResponse,
    TaskTakeResponse,
)
from app.hrms.services import task_assessment_service
from app.utils.pagination import page_result_to_dict

# Everyone who plays some part in this feature - per-record ownership (bank/task
# creator) and the HR/Admin-only trainee-assignment rule are enforced inside the
# service layer, this just keeps out roles with no stake in it at all.
TASK_ROLES = (Role.ADMIN, Role.HR, Role.TEAM_MEMBER)

router = APIRouter(
    prefix="/api/hrms/task-assessments",
    tags=["hrms-task-assessments"],
    dependencies=[Depends(require_role(*TASK_ROLES))],
)


# ---------------------------------------------------------------------------
# Question banks
# ---------------------------------------------------------------------------


@router.post("/banks", response_model=BankResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.HR))])
async def create_bank(
    payload: BankCreateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    return await task_assessment_service.create_bank(hrms_db, kms_db, current_user, payload)


@router.get("/banks", dependencies=[Depends(require_role(Role.ADMIN, Role.HR))])
async def list_banks(
    page: int = 0,
    size: int = 10,
    search: str | None = None,
    account_id: int | None = None,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await task_assessment_service.list_banks(hrms_db, kms_db, current_user, page, size, search, account_id)
    return page_result_to_dict(result, lambda item: item)


@router.get(
    "/banks/{bank_id}", response_model=BankResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.HR))]
)
async def get_bank(
    bank_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await task_assessment_service.get_bank(hrms_db, kms_db, current_user, bank_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found")
    return result


@router.put("/banks/{bank_id}", response_model=BankResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.HR))])
async def update_bank(
    bank_id: int,
    payload: BankUpdateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await task_assessment_service.update_bank(hrms_db, kms_db, current_user, bank_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found or not yours to manage")
    return result


@router.patch(
    "/banks/{bank_id}/active", response_model=BankResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.HR))]
)
async def set_bank_active(
    bank_id: int,
    is_active: bool,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await task_assessment_service.set_bank_active(hrms_db, kms_db, current_user, bank_id, is_active)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found or not yours to manage")
    return result


# ---------------------------------------------------------------------------
# Bank questions
# ---------------------------------------------------------------------------


@router.get("/banks/{bank_id}/questions", dependencies=[Depends(require_role(Role.ADMIN, Role.HR))])
async def list_questions(
    bank_id: int,
    module_name: str | None = None,
    page: int = 0,
    size: int = 20,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.list_questions(hrms_db, current_user, bank_id, module_name, page, size)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found")
    return page_result_to_dict(result, lambda item: item)


@router.get(
    "/banks/{bank_id}/module-names",
    response_model=list[str],
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def list_module_names(
    bank_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.list_module_names(hrms_db, current_user, bank_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found")
    return result


@router.post(
    "/banks/{bank_id}/questions",
    response_model=BankQuestionResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def add_question(
    bank_id: int,
    payload: BankQuestionCreateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.add_question(hrms_db, current_user, bank_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found or not yours to manage")
    return result


@router.get(
    "/questions/template",
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def download_question_template():
    content = task_assessment_service.build_question_template_xlsx()
    return Response(
        content=content,
        media_type=EXCEL_SHEET_CONTENT_TYPE,
        headers={"Content-Disposition": "attachment; filename=question_bank_template.xlsx"},
    )


@router.post(
    "/banks/{bank_id}/questions/import",
    response_model=BankQuestionImportResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def import_questions(
    bank_id: int,
    file: UploadFile = File(...),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    content = await file.read()
    result = await task_assessment_service.import_questions(hrms_db, current_user, bank_id, file.filename or "", content)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question bank not found or not yours to manage")
    return result


@router.get(
    "/banks/{bank_id}/questions/{question_id}",
    response_model=BankQuestionResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def get_question(
    bank_id: int,
    question_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.get_question(hrms_db, current_user, bank_id, question_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return result


@router.put(
    "/banks/{bank_id}/questions/{question_id}",
    response_model=BankQuestionResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def update_question(
    bank_id: int,
    question_id: int,
    payload: BankQuestionUpdateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.update_question(hrms_db, current_user, bank_id, question_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found or not yours to manage")
    return result


@router.patch(
    "/banks/{bank_id}/questions/{question_id}/active",
    response_model=BankQuestionResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def set_question_active(
    bank_id: int,
    question_id: int,
    is_active: bool,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.set_question_active(hrms_db, current_user, bank_id, question_id, is_active)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found or not yours to manage")
    return result


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@router.post(
    "/tasks", response_model=TaskManageDetailResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.HR))]
)
async def create_task(
    payload: TaskCreateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        return await task_assessment_service.create_task(hrms_db, current_user, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/tasks")
async def list_tasks(
    page: int = 0,
    size: int = 10,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.list_tasks(hrms_db, current_user, page, size)
    return page_result_to_dict(result, lambda item: item)


@router.get(
    "/tasks/by-training/{training_id}",
    response_model=list[TaskManageDetailResponse],
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def list_tasks_for_training(
    training_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    return await task_assessment_service.list_tasks_for_training(hrms_db, current_user, training_id)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    management_view = await task_assessment_service.get_task_for_management(hrms_db, current_user, task_id)
    if management_view is not None:
        return management_view
    trainee_view = await task_assessment_service.get_task_for_trainee(hrms_db, current_user, task_id)
    if trainee_view is not None:
        return trainee_view
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post(
    "/tasks/{task_id}/assign",
    response_model=TaskManageDetailResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def assign_trainees(
    task_id: int,
    payload: AssignTraineesRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.assign_trainees(hrms_db, current_user, task_id, payload.trainee_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result


@router.post(
    "/tasks/{task_id}/assign-by-location",
    response_model=TaskManageDetailResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def assign_trainees_by_location(
    task_id: int,
    payload: AssignByLocationRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.assign_trainees_by_location(
            hrms_db, current_user, task_id, payload.work_location
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result


@router.post("/tasks/{task_id}/close", response_model=TaskManageDetailResponse)
async def close_task(
    task_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.close_task(hrms_db, current_user, task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not yours to manage")
    return result


@router.post("/tasks/{task_id}/start", response_model=TaskTakeResponse)
async def start_task(
    task_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.start_or_resume(hrms_db, current_user, task_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not assigned to you")
    return result


@router.put("/tasks/{task_id}/questions/{task_question_id}/answer")
async def save_answer(
    task_id: int,
    task_question_id: int,
    payload: AnswerSaveRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.save_answer(hrms_db, current_user, task_id, task_question_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not assigned to you")
    return result


@router.post("/tasks/{task_id}/submit", response_model=TaskResultResponse)
async def submit_task(
    task_id: int,
    payload: SubmitTaskRequest = SubmitTaskRequest(),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.submit_task(hrms_db, current_user, task_id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not assigned to you")
    return result


@router.post("/tasks/{task_id}/retry", response_model=RetryResponse)
async def retry_task(
    task_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.retry_task(hrms_db, current_user, task_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not assigned to you")
    return result


@router.post(
    "/tasks/{task_id}/assignees/{trainee_id}/reassign",
    response_model=TaskManageDetailResponse,
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)
async def reassign_task(
    task_id: int,
    trainee_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        result = await task_assessment_service.reassign_task(hrms_db, current_user, task_id, trainee_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result


@router.get("/tasks/{task_id}/my-result", response_model=TaskResultResponse)
async def get_my_result(
    task_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.get_my_result(hrms_db, current_user, task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not assigned to you")
    return result


@router.get("/tasks/{task_id}/report", response_model=TaskReportResponse)
async def get_report(
    task_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await task_assessment_service.get_report(hrms_db, current_user, task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not yours to manage")
    return result
