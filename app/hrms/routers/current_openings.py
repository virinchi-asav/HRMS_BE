from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import ADMIN_MANAGER_BUHEAD
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.current_opening import CurrentOpeningResponse, CurrentOpeningUpsertRequest
from app.hrms.services import current_opening_service
from app.utils.pagination import page_result_to_dict

router = APIRouter(
    prefix="/api/hrms/current-openings",
    tags=["hrms-current-openings"],
    dependencies=[Depends(require_role(*ADMIN_MANAGER_BUHEAD))],
)


@router.get("")
async def list_current_openings(page: int = 0, size: int = 10, db: AsyncSession = Depends(get_hrms_db)):
    result = await current_opening_service.list_current_openings(db, page, size)
    return page_result_to_dict(result, lambda e: CurrentOpeningResponse.model_validate(e).model_dump())


@router.get("/form-options")
async def form_options(db: AsyncSession = Depends(get_hrms_db)):
    return await current_opening_service.get_form_options(db)


@router.post("", response_model=CurrentOpeningResponse)
async def create_current_opening(payload: CurrentOpeningUpsertRequest, db: AsyncSession = Depends(get_hrms_db)):
    return await current_opening_service.create_current_opening(db, payload)


@router.get("/{opening_id}", response_model=CurrentOpeningResponse)
async def get_current_opening(opening_id: int, db: AsyncSession = Depends(get_hrms_db)):
    entity = await current_opening_service.get_current_opening(db, opening_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current opening not found")
    return entity


@router.put("/{opening_id}", response_model=CurrentOpeningResponse)
async def update_current_opening(
    opening_id: int, payload: CurrentOpeningUpsertRequest, db: AsyncSession = Depends(get_hrms_db)
):
    entity = await current_opening_service.update_current_opening(db, opening_id, payload)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current opening not found")
    return entity


@router.delete("/{opening_id}")
async def delete_current_opening(opening_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await current_opening_service.delete_current_opening(db, opening_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current opening not found")
    return {"message": "Current opening deleted"}


@router.post("/{opening_id}/restore")
async def restore_current_opening(opening_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await current_opening_service.restore_current_opening(db, opening_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current opening not found")
    return {"message": "Current opening restored"}
