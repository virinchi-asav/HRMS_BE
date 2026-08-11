from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import ADMIN_ONLY
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.client import ClientResponse
from app.hrms.schemas.survey import SurveyResponse, SurveySubmissionRequest
from app.hrms.services import survey_service
from app.utils.pagination import page_result_to_dict

router = APIRouter(prefix="/api/hrms/survey", tags=["hrms-survey"])
admin_router = APIRouter(
    prefix="/api/hrms/admin/survey", tags=["hrms-admin"], dependencies=[Depends(require_role(*ADMIN_ONLY))]
)


@router.get("/client/{username}", response_model=ClientResponse)
async def get_client_by_username(username: str, db: AsyncSession = Depends(get_hrms_db)):
    client = await survey_service.get_client_by_username(db, username)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.post("/submit", response_model=SurveyResponse)
async def submit_survey(payload: SurveySubmissionRequest, db: AsyncSession = Depends(get_hrms_db)):
    return await survey_service.submit_survey(db, payload)


@admin_router.get("/results")
async def list_survey_results(page: int = 0, size: int = 10, search: str | None = None, db: AsyncSession = Depends(get_hrms_db)):
    result = await survey_service.list_survey_results(db, page, size, search)
    return page_result_to_dict(result, lambda s: SurveyResponse.model_validate(s).model_dump())


@admin_router.get("/export")
async def export_survey_results(db: AsyncSession = Depends(get_hrms_db)):
    content = await survey_service.export_surveys_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Survey_Report.xlsx"},
    )
