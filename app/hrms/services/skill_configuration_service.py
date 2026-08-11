from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.skill_configuration import SkillConfigurationEntity
from app.hrms.models.user import UserEntity
from app.hrms.schemas.skill_configuration import SkillConfigurationUpsertRequest
from app.utils.pagination import PageResult, paginate


async def list_skill_configurations(
    db: AsyncSession,
    page_number: int,
    page_size: int,
    search: str | None,
    department: str | None,
    skill_category: str | None,
) -> PageResult:
    stmt = select(SkillConfigurationEntity).where(SkillConfigurationEntity.deleted_at.is_(None))
    if search:
        stmt = stmt.where(
            or_(
                SkillConfigurationEntity.skill_name.ilike(f"%{search}%"),
                SkillConfigurationEntity.skill_category.ilike(f"%{search}%"),
            )
        )
    if department:
        stmt = stmt.where(SkillConfigurationEntity.department == department)
    if skill_category:
        stmt = stmt.where(SkillConfigurationEntity.skill_category == skill_category)
    stmt = stmt.order_by(SkillConfigurationEntity.id.desc())
    return await paginate(db, stmt, page_number, page_size)


async def get_skill_configuration(db: AsyncSession, config_id: int) -> SkillConfigurationEntity | None:
    entity = await db.get(SkillConfigurationEntity, config_id)
    if entity is None or entity.deleted_at is not None:
        return None
    return entity


async def create_skill_configuration(
    db: AsyncSession, data: SkillConfigurationUpsertRequest
) -> SkillConfigurationEntity:
    entity = SkillConfigurationEntity(
        skill_name=data.skill_name,
        skill_category=data.skill_category,
        department=data.department,
        is_sub_skill_is_available=int(data.is_sub_skill_is_available),
        status=int(data.status),
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def update_skill_configuration(
    db: AsyncSession, config_id: int, data: SkillConfigurationUpsertRequest
) -> SkillConfigurationEntity | None:
    entity = await get_skill_configuration(db, config_id)
    if entity is None:
        return None
    entity.skill_name = data.skill_name
    entity.skill_category = data.skill_category
    entity.department = data.department
    entity.is_sub_skill_is_available = int(data.is_sub_skill_is_available)
    entity.status = int(data.status)
    await db.commit()
    await db.refresh(entity)
    return entity


async def delete_skill_configuration(db: AsyncSession, config_id: int) -> bool:
    entity = await get_skill_configuration(db, config_id)
    if entity is None:
        return False
    entity.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def restore_skill_configuration(db: AsyncSession, config_id: int) -> bool:
    entity = await db.get(SkillConfigurationEntity, config_id)
    if entity is None:
        return False
    entity.deleted_at = None
    await db.commit()
    return True


async def get_departments(db: AsyncSession) -> list[str]:
    result = await db.execute(select(UserEntity.department).where(UserEntity.department.is_not(None)).distinct())
    return sorted(set(result.scalars().all()))


async def get_skill_categories(db: AsyncSession, department: str | None) -> list[str]:
    stmt = select(SkillConfigurationEntity.skill_category).where(
        SkillConfigurationEntity.skill_category.is_not(None), SkillConfigurationEntity.skill_category != ""
    )
    if department:
        stmt = stmt.where(SkillConfigurationEntity.department == department)
    result = await db.execute(stmt.distinct())
    return sorted(set(result.scalars().all()))
