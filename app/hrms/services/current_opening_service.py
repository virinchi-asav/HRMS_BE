from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.current_opening import CurrentOpeningEntity
from app.hrms.models.skill import SkillEntity
from app.hrms.models.sub_skill import SubSkillEntity
from app.hrms.models.user import UserEntity
from app.hrms.schemas.current_opening import CurrentOpeningUpsertRequest
from app.utils.pagination import PageResult, paginate


async def list_current_openings(db: AsyncSession, page_number: int, page_size: int) -> PageResult:
    stmt = (
        select(CurrentOpeningEntity)
        .where(CurrentOpeningEntity.deleted_at.is_(None))
        .order_by(CurrentOpeningEntity.id.desc())
    )
    return await paginate(db, stmt, page_number, page_size)


async def get_current_opening(db: AsyncSession, opening_id: int) -> CurrentOpeningEntity | None:
    entity = await db.get(CurrentOpeningEntity, opening_id)
    if entity is None or entity.deleted_at is not None:
        return None
    return entity


async def create_current_opening(db: AsyncSession, data: CurrentOpeningUpsertRequest) -> CurrentOpeningEntity:
    entity = CurrentOpeningEntity(**data.model_dump())
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def update_current_opening(
    db: AsyncSession, opening_id: int, data: CurrentOpeningUpsertRequest
) -> CurrentOpeningEntity | None:
    entity = await get_current_opening(db, opening_id)
    if entity is None:
        return None
    for field, value in data.model_dump().items():
        setattr(entity, field, value)
    await db.commit()
    await db.refresh(entity)
    return entity


async def delete_current_opening(db: AsyncSession, opening_id: int) -> bool:
    entity = await get_current_opening(db, opening_id)
    if entity is None:
        return False
    entity.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def restore_current_opening(db: AsyncSession, opening_id: int) -> bool:
    entity = await db.get(CurrentOpeningEntity, opening_id)
    if entity is None:
        return False
    entity.deleted_at = None
    await db.commit()
    return True


async def get_form_options(db: AsyncSession) -> dict:
    """Mirrors createEditCurrentOpeningsForm's dropdown data: a de-duplicated skill name
    list (from Skill + SubSkill), plus distinct account/department lists from users."""
    skill_names = set((await db.execute(select(SkillEntity.skill_name))).scalars().all())
    skill_names |= set((await db.execute(select(SubSkillEntity.skill_name))).scalars().all())

    accounts = (
        (await db.execute(select(UserEntity.project_name).where(UserEntity.project_name.is_not(None)).distinct()))
        .scalars()
        .all()
    )
    departments = (
        (await db.execute(select(UserEntity.department).where(UserEntity.department.is_not(None)).distinct()))
        .scalars()
        .all()
    )

    return {
        "skills": sorted(skill_names),
        "accounts": sorted(set(accounts)),
        "departments": sorted(set(departments)),
    }
