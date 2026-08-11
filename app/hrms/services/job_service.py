from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.job import JobEntity
from app.hrms.schemas.job import JobUpsertRequest


async def list_jobs(db: AsyncSession) -> list[JobEntity]:
    """Mirrors JobsController::index - Jobs::withTrashed()->get(): ALL jobs including
    soft-deleted ones (so the admin UI can offer restore), no pagination."""
    result = await db.execute(select(JobEntity).order_by(JobEntity.id.desc()))
    return list(result.scalars().all())


async def list_active_jobs(db: AsyncSession) -> list[JobEntity]:
    """Mirrors MksController::Career - Jobs::withoutTrashed()->get() for the public
    careers listing page."""
    result = await db.execute(
        select(JobEntity).where(JobEntity.deleted_at.is_(None)).order_by(JobEntity.id.desc())
    )
    return list(result.scalars().all())


async def get_job(db: AsyncSession, job_id: int) -> JobEntity | None:
    return await db.get(JobEntity, job_id)


async def create_job(db: AsyncSession, data: JobUpsertRequest) -> JobEntity:
    entity = JobEntity(**data.model_dump())
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def update_job(db: AsyncSession, job_id: int, data: JobUpsertRequest) -> JobEntity | None:
    entity = await get_job(db, job_id)
    if entity is None:
        return None
    for field, value in data.model_dump().items():
        setattr(entity, field, value)
    await db.commit()
    await db.refresh(entity)
    return entity


async def delete_job(db: AsyncSession, job_id: int) -> bool:
    entity = await get_job(db, job_id)
    if entity is None:
        return False
    entity.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def restore_job(db: AsyncSession, job_id: int) -> bool:
    entity = await get_job(db, job_id)
    if entity is None:
        return False
    entity.deleted_at = None
    await db.commit()
    return True
