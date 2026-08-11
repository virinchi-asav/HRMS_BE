from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import ADMIN_OR_HR, Role
from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db, require_role
from app.hrms.schemas.certificate import CertificateIssueRequest, CertificateResponse, CertificateTemplateResponse
from app.hrms.services import certificate_service

router = APIRouter(tags=["hrms-certificates"])


@router.get("/api/hrms/certificate-template", response_model=CertificateTemplateResponse | None)
async def get_certificate_template(
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    if current_user.role not in ADMIN_OR_HR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return await certificate_service.get_current_template_response(hrms_db, request)


@router.post(
    "/api/hrms/certificate-template",
    response_model=CertificateTemplateResponse,
    dependencies=[Depends(require_role(*ADMIN_OR_HR))],
)
async def upload_certificate_template(
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    content = await file.read()
    await certificate_service.upload_template(hrms_db, current_user, content, file.filename)
    return await certificate_service.get_current_template_response(hrms_db, request)


@router.get(
    "/api/hrms/training/{training_id}/certificates",
    response_model=list[CertificateResponse],
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR, Role.BU_HEAD, Role.TEAM_MEMBER))],
)
async def list_certificates(
    training_id: int,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    result = await certificate_service.list_certificates(hrms_db, request, current_user, training_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
    return result


@router.post(
    "/api/hrms/training/{training_id}/certificates",
    response_model=CertificateResponse,
    dependencies=[Depends(require_role(*ADMIN_OR_HR))],
)
async def issue_certificate(
    training_id: int,
    payload: CertificateIssueRequest,
    request: Request,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    try:
        return await certificate_service.issue_certificate(hrms_db, request, current_user, training_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
