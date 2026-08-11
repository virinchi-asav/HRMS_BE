from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import Role
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.job import JobResponse, JobUpsertRequest
from app.hrms.services import job_service

# Internal job management (list/create/edit/delete/restore) is Admin/HR/BU Head only -
# the public careers listing/apply flow below is a separate, unauthenticated router and
# is deliberately untouched.
router = APIRouter(
    prefix="/api/hrms/jobs", tags=["hrms-jobs"], dependencies=[Depends(require_role(Role.ADMIN, Role.HR, Role.BU_HEAD))]
)

public_router = APIRouter(prefix="/api/hrms/public/jobs", tags=["hrms-public"])


@router.get("", response_model=list[JobResponse])
async def list_jobs(db: AsyncSession = Depends(get_hrms_db)):
    """Mirrors JobsController::index - includes soft-deleted jobs for the admin's
    restore UI, no pagination (matches the source app exactly)."""
    return await job_service.list_jobs(db)


@router.post("", response_model=JobResponse)
async def create_job(payload: JobUpsertRequest, db: AsyncSession = Depends(get_hrms_db)):
    return await job_service.create_job(db, payload)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_hrms_db)):
    entity = await job_service.get_job(db, job_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return entity


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: int, payload: JobUpsertRequest, db: AsyncSession = Depends(get_hrms_db)):
    entity = await job_service.update_job(db, job_id, payload)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return entity


@router.delete("/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await job_service.delete_job(db, job_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job deleted"}


@router.post("/{job_id}/restore")
async def restore_job(job_id: int, db: AsyncSession = Depends(get_hrms_db)):
    ok = await job_service.restore_job(db, job_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job restored"}


@public_router.get("", response_model=list[JobResponse])
async def list_public_jobs(db: AsyncSession = Depends(get_hrms_db)):
    """Mirrors MksController::Career - the public careers listing page."""
    return await job_service.list_active_jobs(db)


@public_router.get("/{job_id}", response_model=JobResponse)
async def get_public_job(job_id: int, db: AsyncSession = Depends(get_hrms_db)):
    entity = await job_service.get_job(db, job_id)
    if entity is None or entity.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return entity
