from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db, require_role
from app.hrms.schemas.training import (
    AssessmentResponse,
    AssessmentReviewRequest,
    AssessmentSubmissionUpdateRequest,
    CommentCreateRequest,
    CommentResponse,
    DayEntryCreateRequest,
    DayEntryResponse,
    MaterialLinkCreateRequest,
    MaterialResponse,
    RejectRequest,
    TrainingCreateRequest,
    TrainingResponse,
)
from app.hrms.services import training_service
from app.utils.pagination import page_result_to_dict

# Everyone who plays some part in the workflow (creator, approver, trainer, trainee) -
# per-record ownership is enforced inside the service layer, this just keeps out roles
# with no role in training at all (Manager, Candidate).
TRAINING_ROLES = (Role.ADMIN, Role.HR, Role.BU_HEAD, Role.TEAM_MEMBER)

router = APIRouter(
    prefix="/api/hrms/training",
    tags=["hrms-training"],
    dependencies=[Depends(require_role(*TRAINING_ROLES))],
)


@router.post("", response_model=TrainingResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.HR))])
async def create_training(
    payload: TrainingCreateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    try:
        return await training_service.create_training(hrms_db, kms_db, current_user, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("")
async def list_trainings(
    page: int = 0,
    size: int = 10,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await training_service.list_trainings(hrms_db, kms_db, current_user, page, size)
    return page_result_to_dict(result, lambda item: item)


@router.get("/{training_id}", response_model=TrainingResponse)
async def get_training(
    training_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await training_service.get_training(hrms_db, kms_db, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return result


@router.post("/{training_id}/approve", response_model=TrainingResponse)
async def approve_training(
    training_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await training_service.approve_training(hrms_db, kms_db, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or not awaiting your approval")
    return result


@router.post("/{training_id}/reject", response_model=TrainingResponse)
async def reject_training(
    training_id: int,
    payload: RejectRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await training_service.reject_training(hrms_db, kms_db, current_user, training_id, payload.reason)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or not awaiting your approval")
    return result


@router.post("/{training_id}/complete", response_model=TrainingResponse)
async def complete_training(
    training_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await training_service.mark_completed(hrms_db, kms_db, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or not in progress")
    return result


@router.get("/{training_id}/day-entries", response_model=list[DayEntryResponse])
async def list_day_entries(
    training_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.list_day_entries(hrms_db, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return result


@router.post("/{training_id}/day-entries", response_model=DayEntryResponse)
async def add_day_entry(
    training_id: int,
    payload: DayEntryCreateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.add_day_entry(hrms_db, current_user, training_id, payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or not yours to update"
        )
    return result


@router.get("/{training_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    training_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.list_comments(hrms_db, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return result


@router.post("/{training_id}/comments", response_model=CommentResponse)
async def add_comment(
    training_id: int,
    payload: CommentCreateRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.add_comment(hrms_db, current_user, training_id, payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or you're not a participant"
        )
    return result


@router.get("/{training_id}/materials", response_model=list[MaterialResponse])
async def list_materials(
    training_id: int,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.list_materials(hrms_db, request, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return result


@router.post("/{training_id}/materials", response_model=MaterialResponse)
async def add_material_link(
    training_id: int,
    payload: MaterialLinkCreateRequest,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.add_material_link(hrms_db, request, current_user, training_id, payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or not yours to update"
        )
    return result


@router.post("/{training_id}/materials/upload", response_model=MaterialResponse)
async def add_material_document(
    training_id: int,
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    content = await file.read()
    result = await training_service.add_material_document(
        hrms_db, request, current_user, training_id, title, content, file.filename
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Training not found or not yours to update"
        )
    return result


@router.post("/{training_id}/assessments", response_model=AssessmentResponse)
async def create_assessment(
    training_id: int,
    request: Request,
    trainee_id: int = Form(...),
    description: str = Form(...),
    detail_document: UploadFile | None = File(default=None),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    content = await detail_document.read() if detail_document is not None else None
    filename = detail_document.filename if detail_document is not None else None
    try:
        return await training_service.create_assessment(
            hrms_db, request, current_user, training_id, trainee_id, description, content, filename
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{training_id}/assessments", response_model=list[AssessmentResponse])
async def list_assessments(
    training_id: int,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.list_assessments(hrms_db, request, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return result


@router.get("/{training_id}/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    training_id: int,
    assessment_id: int,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.get_assessment(hrms_db, request, current_user, training_id, assessment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return result


@router.patch("/{training_id}/assessments/{assessment_id}/submission", response_model=AssessmentResponse)
async def update_submission(
    training_id: int,
    assessment_id: int,
    payload: AssessmentSubmissionUpdateRequest,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.update_submission(
        hrms_db, request, current_user, training_id, assessment_id, payload
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found or not yours to update"
        )
    return result


@router.post("/{training_id}/assessments/{assessment_id}/screenshots", response_model=AssessmentResponse)
async def add_screenshots(
    training_id: int,
    assessment_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one file is required")
    result = None
    for f in files:
        content = await f.read()
        result = await training_service.add_screenshot(
            hrms_db, request, current_user, training_id, assessment_id, content, f.filename
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found or not yours to update"
            )
    return result


@router.delete("/{training_id}/assessments/{assessment_id}/screenshots/{screenshot_id}")
async def delete_screenshot(
    training_id: int,
    assessment_id: int,
    screenshot_id: int,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    ok = await training_service.delete_screenshot(hrms_db, current_user, training_id, assessment_id, screenshot_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found or not yours to update"
        )
    return {"message": "Screenshot removed"}


@router.post("/{training_id}/assessments/{assessment_id}/zip", response_model=AssessmentResponse)
async def upload_project_zip(
    training_id: int,
    assessment_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    content = await file.read()
    result = await training_service.upload_project_zip(
        hrms_db, request, current_user, training_id, assessment_id, content, file.filename
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found or not yours to update"
        )
    return result


@router.post("/{training_id}/assessments/{assessment_id}/review", response_model=AssessmentResponse)
async def review_assessment(
    training_id: int,
    assessment_id: int,
    payload: AssessmentReviewRequest,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await training_service.review_assessment(
        hrms_db, request, current_user, training_id, assessment_id, payload
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found or not ready for review"
        )
    return result
