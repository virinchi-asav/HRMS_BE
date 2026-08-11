from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.reports import KmsUsageReportResponse, TrainingReportResponse
from app.hrms.services import reports_service

router = APIRouter(
    prefix="/api/hrms/reports",
    tags=["hrms-reports"],
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR))],
)


@router.get("/trainings", response_model=TrainingReportResponse)
async def get_training_report(
    months: int = 6,
    account_ids: list[int] | None = Query(default=None),
    department_ids: list[int] | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    sort: str | None = None,
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    if months <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="months must be greater than 0")
    return await reports_service.get_training_report(
        hrms_db, kms_db, months, account_ids, department_ids, status_filter, sort
    )


@router.get("/kms-usage", response_model=KmsUsageReportResponse)
async def get_kms_usage_report(
    days: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    account_id: int | None = None,
    hrms_db: AsyncSession = Depends(get_hrms_db),
    kms_db: AsyncSession = Depends(get_db),
):
    if days is not None and days <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="days must be greater than 0")
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date cannot be before start_date")
    return await reports_service.get_kms_usage_report(hrms_db, kms_db, days, start_date, end_date, account_id)
