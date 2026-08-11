from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import Role
from app.hrms.core.deps import get_hrms_db, require_role
from app.hrms.schemas.candidate import CandidateApplyRequest, CandidateResponse
from app.hrms.services import candidate_service
from app.utils.pagination import page_result_to_dict

# Internal candidate management is Admin/HR/BU Head only - the public apply-for-a-job
# flow below is a separate, unauthenticated router and is deliberately untouched.
router = APIRouter(
    prefix="/api/hrms/candidates",
    tags=["hrms-candidates"],
    dependencies=[Depends(require_role(Role.ADMIN, Role.HR, Role.BU_HEAD))],
)
public_router = APIRouter(prefix="/api/hrms/public/candidates", tags=["hrms-public"])


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(db: AsyncSession = Depends(get_hrms_db)):
    return await candidate_service.list_candidates(db)


@router.get("/hr-profiles")
async def hr_view_profiles(
    page: int = 0,
    size: int = 10,
    role: int | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_hrms_db),
):
    from app.hrms.schemas.user import UserListItem

    result = await candidate_service.hr_view_profiles(db, page, size, role, search)
    return page_result_to_dict(result, lambda u: UserListItem.model_validate(u).model_dump())


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: int, db: AsyncSession = Depends(get_hrms_db)):
    entity = await candidate_service.get_candidate(db, candidate_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return entity


@public_router.post("/apply", response_model=CandidateResponse)
async def apply_for_job(
    request: Request,
    job_id: int = Form(...),
    candidate_name: str = Form(...),
    candidate_number: int = Form(...),
    candidate_email: str = Form(...),
    candidate_doj: int = Form(...),
    candidate_job_title: str | None = Form(None),
    candidate_address: str | None = Form(None),
    candidate_pin_code: str | None = Form(None),
    candidate_city: str | None = Form(None),
    candidate_state: str | None = Form(None),
    candidate_experience_yrs: int | None = Form(None),
    candidate_experience_month: int | None = Form(None),
    candidate_employer: str | None = Form(None),
    candidate_location: str | None = Form(None),
    candidate_ctc: str | None = Form(None),
    candidate_expected_ctc: str | None = Form(None),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_hrms_db),
):
    if resume is None or not candidate_service.is_valid_resume(resume):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume is required and must be one of: docx, pdf, jpg, png",
        )

    data = CandidateApplyRequest(
        job_id=job_id,
        candidate_name=candidate_name,
        candidate_number=candidate_number,
        candidate_email=candidate_email,
        candidate_address=candidate_address,
        candidate_pin_code=candidate_pin_code,
        candidate_city=candidate_city,
        candidate_state=candidate_state,
        candidate_job_title=candidate_job_title,
        candidate_experience_yrs=candidate_experience_yrs,
        candidate_experience_month=candidate_experience_month,
        candidate_employer=candidate_employer,
        candidate_location=candidate_location,
        candidate_ctc=candidate_ctc,
        candidate_expected_ctc=candidate_expected_ctc,
        candidate_doj=candidate_doj,
    )
    return await candidate_service.apply_for_job(db, request, data, resume)
