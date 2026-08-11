from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import ADMIN_ONLY
from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db, require_role
from app.hrms.models.user import UserEntity
from app.hrms.schemas.update_request import UpdateRequestAction, UpdateRequestCreate, UpdateRequestResponse
from app.hrms.schemas.user import ProfileReviewRequest, UserResponse
from app.hrms.services import admin_service

router = APIRouter(prefix="/api/hrms/admin", tags=["hrms-admin"], dependencies=[Depends(require_role(*ADMIN_ONLY))])
requests_router = APIRouter(prefix="/api/hrms/update-requests", tags=["hrms-update-requests"], dependencies=[Depends(get_current_hrms_user)])


@requests_router.post("", response_model=UpdateRequestResponse)
async def request_profile_update(
    payload: UpdateRequestCreate,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    """Mirrors CandidateController::requestUpdate."""
    user = await db.get(UserEntity, current_user.id)
    entity = await admin_service.create_update_request(db, user, payload.reason)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are already allowed to update your profile."
        )
    return entity


@router.get("/update-requests", response_model=list[UpdateRequestResponse])
async def list_pending_update_requests(db: AsyncSession = Depends(get_hrms_db)):
    return await admin_service.list_pending_update_requests(db)


@router.get("/update-requests/all", response_model=list[UpdateRequestResponse])
async def list_all_update_requests(db: AsyncSession = Depends(get_hrms_db)):
    return await admin_service.list_all_update_requests(db)


@router.post("/update-requests/{request_id}", response_model=UpdateRequestResponse)
async def handle_update_request(request_id: int, payload: UpdateRequestAction, db: AsyncSession = Depends(get_hrms_db)):
    entity = await admin_service.handle_update_request(db, request_id, payload.action, payload.admin_note)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update request not found")
    return entity


@router.get("/profiles/pending", response_model=list[UserResponse])
async def get_pending_profiles(db: AsyncSession = Depends(get_hrms_db)):
    return await admin_service.get_pending_profiles(db)


@router.get("/profiles/{user_id}", response_model=UserResponse)
async def get_profile_for_review(user_id: int, db: AsyncSession = Depends(get_hrms_db)):
    user = await admin_service.get_profile_for_review(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/profiles/{user_id}/review", response_model=UserResponse)
async def submit_profile_review(
    user_id: int,
    payload: ProfileReviewRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    user = await admin_service.submit_profile_review(db, user_id, current_user.id, payload.admin_message, payload.status)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/export-candidates")
async def export_candidates(db: AsyncSession = Depends(get_hrms_db)):
    """Mirrors AdminController::exportCandidates - the source route had NO auth at all;
    gated to Admin here since exporting candidate PII without auth was clearly
    unintended (see the "fix obvious bugs" decision)."""
    content = await admin_service.export_candidates_name_email_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=candidates_export.xlsx"},
    )
