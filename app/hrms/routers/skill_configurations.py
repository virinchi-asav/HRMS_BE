from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import ADMIN_MANAGER_BUHEAD
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.skill_configuration import SkillConfigurationResponse, SkillConfigurationUpsertRequest
from app.hrms.services import skill_configuration_service
from app.utils.pagination import page_result_to_dict

router = APIRouter(
    prefix="/api/hrms/skill-configurations",
    tags=["hrms-skill-configurations"],
    dependencies=[Depends(require_role(*ADMIN_MANAGER_BUHEAD))],
)


@router.get("")
async def list_skill_configurations(
    page: int = 0,
    size: int = 10,
    search: str | None = None,
    department: str | None = None,
    skill_category: str | None = None,
    db: AsyncSession = Depends(get_hrms_db),
):
    result = await skill_configuration_service.list_skill_configurations(
        db, page, size, search, department, skill_category
    )
    return page_result_to_dict(result, lambda e: SkillConfigurationResponse.model_validate(e).model_dump())


@router.get("/departments")
async def get_departments(db: AsyncSession = Depends(get_hrms_db)):
    return await skill_configuration_service.get_departments(db)


@router.get("/skill-categories")
async def get_skill_categories(department: str | None = None, db: AsyncSession = Depends(get_hrms_db)):
    return await skill_configuration_service.get_skill_categories(db, department)


@router.post("", response_model=SkillConfigurationResponse)
async def create_skill_configuration(
    payload: SkillConfigurationUpsertRequest, db: AsyncSession = Depends(get_hrms_db)
):
    return await skill_configuration_service.create_skill_configuration(db, payload)


@router.get("/{config_id}", response_model=SkillConfigurationResponse)
async def get_skill_configuration(config_id: int, db: AsyncSession = Depends(get_hrms_db)):
    entity = await skill_configuration_service.get_skill_configuration(db, config_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill configuration not found")
    return entity


@router.put("/{config_id}", response_model=SkillConfigurationResponse)
async def update_skill_configuration(
    config_id: int, payload: SkillConfigurationUpsertRequest, db: AsyncSession = Depends(get_hrms_db)
):
    entity = await skill_configuration_service.update_skill_configuration(db, config_id, payload)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill configuration not found")
    return entity


@router.delete("/{config_id}")
async def delete_skill_configuration(config_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await skill_configuration_service.delete_skill_configuration(db, config_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill configuration not found")
    return {"message": "Skill configuration deleted"}


@router.post("/{config_id}/restore")
async def restore_skill_configuration(config_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await skill_configuration_service.restore_skill_configuration(db, config_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill configuration not found")
    return {"message": "Skill configuration restored"}
