from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.hrms.core.constants import ADMIN_ONLY, ADMIN_OR_HR
from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db, require_role
from app.hrms.schemas.user import (
    UserAdminUpdateRequest,
    UserCreateRequest,
    UserListItem,
    UserProfileUpdateRequest,
    UserResponse,
)
from app.hrms.services import user_service
from app.models.department import DepartmentEntity
from app.utils.pagination import page_result_to_dict

router = APIRouter(prefix="/api/hrms/users", tags=["hrms-users"], dependencies=[Depends(get_current_hrms_user)])

# FastAPI needs every multipart file field declared explicitly in the function
# signature (no **kwargs support) - this mirrors UserController's $fileFields list.
_NoFile = File(None)


async def _profile_files(
    passport_photo: UploadFile | None = _NoFile,
    latest_cv: UploadFile | None = _NoFile,
    aadhar_card: UploadFile | None = _NoFile,
    pan_card: UploadFile | None = _NoFile,
    marksheet_10th: UploadFile | None = _NoFile,
    marksheet_12th: UploadFile | None = _NoFile,
    sem_1: UploadFile | None = _NoFile,
    sem_2: UploadFile | None = _NoFile,
    sem_3: UploadFile | None = _NoFile,
    sem_4: UploadFile | None = _NoFile,
    sem_5: UploadFile | None = _NoFile,
    sem_6: UploadFile | None = _NoFile,
    sem_7: UploadFile | None = _NoFile,
    sem_8: UploadFile | None = _NoFile,
    pg_sem_1: UploadFile | None = _NoFile,
    pg_sem_2: UploadFile | None = _NoFile,
    pg_sem_3: UploadFile | None = _NoFile,
    pg_sem_4: UploadFile | None = _NoFile,
    consolidated_marksheet: UploadFile | None = _NoFile,
    pg_consolidated_marksheet: UploadFile | None = _NoFile,
) -> dict[str, UploadFile | None]:
    return {
        "passport_photo": passport_photo,
        "latest_cv": latest_cv,
        "aadhar_card": aadhar_card,
        "pan_card": pan_card,
        "marksheet_10th": marksheet_10th,
        "marksheet_12th": marksheet_12th,
        "sem_1": sem_1,
        "sem_2": sem_2,
        "sem_3": sem_3,
        "sem_4": sem_4,
        "sem_5": sem_5,
        "sem_6": sem_6,
        "sem_7": sem_7,
        "sem_8": sem_8,
        "pg_sem_1": pg_sem_1,
        "pg_sem_2": pg_sem_2,
        "pg_sem_3": pg_sem_3,
        "pg_sem_4": pg_sem_4,
        "consolidated_marksheet": consolidated_marksheet,
        "pg_consolidated_marksheet": pg_consolidated_marksheet,
    }


@router.get("/me/profile", response_model=UserResponse)
async def get_my_profile(
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user), db: AsyncSession = Depends(get_hrms_db)
):
    return await user_service.get_user(db, current_user.id)


@router.put("/me/profile", response_model=UserResponse)
async def update_my_profile(
    data: str = Form(...),
    files: dict[str, UploadFile | None] = Depends(_profile_files),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    payload = UserProfileUpdateRequest.model_validate_json(data)
    user = await user_service.get_user(db, current_user.id)
    return await user_service.update_own_profile(db, user, payload, files)


async def _kms_department_names(kms_db: AsyncSession) -> dict[int, str]:
    result = await kms_db.execute(select(DepartmentEntity))
    return {d.department_id: d.department_name for d in result.scalars().all()}


def _to_list_item(u, kms_department_names: dict[int, str]) -> dict:
    item = UserListItem.model_validate(u).model_dump()
    item["kms_department"] = kms_department_names.get(u.kms_department_id)
    return item


@router.get("", dependencies=[Depends(require_role(*ADMIN_OR_HR))])
async def list_users(
    page: int = 0,
    size: int = 10,
    role: int | None = None,
    search: str | None = None,
    account_id: int | None = None,
    work_location: str | None = None,
    db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    result = await user_service.admin_list_users(db, page, size, role, search, account_id, work_location)
    kms_department_names = await _kms_department_names(kms_db)
    return page_result_to_dict(result, lambda u: _to_list_item(u, kms_department_names))


@router.get("/work-locations")
async def get_work_locations():
    return {"work_locations": user_service.get_work_locations()}


@router.post("", response_model=UserResponse, dependencies=[Depends(require_role(*ADMIN_ONLY))])
async def create_user(
    payload: UserCreateRequest, db: AsyncSession = Depends(get_hrms_db), kms_db: AsyncSession = Depends(get_db)
):
    return await user_service.admin_create_user(db, kms_db, payload)


@router.post("/import", dependencies=[Depends(require_role(*ADMIN_ONLY))])
async def import_users(file: UploadFile = File(...), db: AsyncSession = Depends(get_hrms_db)):
    content = await file.read()
    return await user_service.import_users_xlsx(db, content)


@router.get("/export", dependencies=[Depends(require_role(*ADMIN_ONLY))])
async def export_users(db: AsyncSession = Depends(get_hrms_db)):
    content = await user_service.export_candidates_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=users.xlsx"},
    )


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role(*ADMIN_ONLY))])
async def get_user(user_id: int, db: AsyncSession = Depends(get_hrms_db)):
    user = await user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role(*ADMIN_ONLY))])
async def admin_update_user(user_id: int, payload: UserAdminUpdateRequest, db: AsyncSession = Depends(get_hrms_db)):
    user = await user_service.admin_update_user(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", dependencies=[Depends(require_role(*ADMIN_ONLY))])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_hrms_db)):
    try:
        ok = await user_service.delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "User deleted successfully"}


@router.get("/{user_id}/profile", dependencies=[Depends(require_role(*ADMIN_OR_HR))])
async def get_user_profile_for_admin(
    user_id: int, db: AsyncSession = Depends(get_hrms_db), kms_db: AsyncSession = Depends(get_db)
):
    user = await user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    kms_department_names = await _kms_department_names(kms_db)
    return {
        "user": UserResponse.model_validate(user).model_dump(),
        "reporting_candidates": [
            _to_list_item(u, kms_department_names) for u in await user_service.get_reporting_candidates(db)
        ],
    }


@router.put("/{user_id}/profile", response_model=UserResponse, dependencies=[Depends(require_role(*ADMIN_OR_HR))])
async def update_user_profile_as_admin(
    user_id: int,
    data: str = Form(...),
    files: dict[str, UploadFile | None] = Depends(_profile_files),
    db: AsyncSession = Depends(get_hrms_db),
):
    payload = UserProfileUpdateRequest.model_validate_json(data)
    user = await user_service.update_user_profile_as_admin(db, user_id, payload, files)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
