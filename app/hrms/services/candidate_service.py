from datetime import datetime

from fastapi import Request, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.config import hrms_settings
from app.hrms.core.constants import Role
from app.hrms.models.candidate import CandidateEntity
from app.hrms.models.user import UserEntity
from app.hrms.schemas.candidate import CandidateApplyRequest
from app.hrms.services import email_service, file_storage_service
from app.utils.pagination import PageResult, paginate

ALLOWED_RESUME_EXTENSIONS = {".docx", ".pdf", ".jpg", ".jpeg", ".png"}
MAX_RESUME_SIZE_BYTES = 2048 * 1024  # 2048 KB, matches Laravel's max:2048 (in KB)


def is_valid_resume(resume: UploadFile) -> bool:
    ext = "." + resume.filename.rsplit(".", 1)[-1].lower() if "." in resume.filename else ""
    return ext in ALLOWED_RESUME_EXTENSIONS


async def apply_for_job(
    db: AsyncSession, request: Request, data: CandidateApplyRequest, resume: UploadFile
) -> CandidateEntity:
    """Mirrors CandidateController::candidate_store (the working, wired-up duplicate of
    MksController::candidate_store)."""
    content = await resume.read()
    stored_name = file_storage_service.unique_filename(resume.filename)
    await file_storage_service.save_file(file_storage_service.candidate_resume_dir(), stored_name, content)
    resume_url = file_storage_service.build_public_url(request, stored_name)

    entity = CandidateEntity(
        job_id=data.job_id,
        candidate_name=data.candidate_name,
        candidate_number=data.candidate_number,
        candidate_email=data.candidate_email,
        candidate_address=data.candidate_address,
        candidate_pin_code=data.candidate_pin_code,
        candidate_city=data.candidate_city,
        candidate_state=data.candidate_state,
        candidate_job_title=data.candidate_job_title,
        candidate_experience_yrs=data.candidate_experience_yrs,
        candidate_experience_month=data.candidate_experience_month,
        candidate_employer=data.candidate_employer,
        candidate_location=data.candidate_location,
        candidate_ctc=data.candidate_ctc,
        candidate_expected_ctc=data.candidate_expected_ctc,
        candidate_doj=data.candidate_doj,
        candidate_resume=resume_url,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    notify_email = hrms_settings.hrms_candidate_submission_notify_email
    if notify_email:
        html = (
            f"<p>New job application received.</p>"
            f"<p><b>Name:</b> {data.candidate_name}<br>"
            f"<b>Email:</b> {data.candidate_email}<br>"
            f"<b>Job title applied for:</b> {data.candidate_job_title or ''}</p>"
            f"<p><a href='{resume_url}'>View resume</a></p>"
        )
        await email_service.send_email(notify_email, "New Candidate Application", html)

    return entity


async def get_candidate(db: AsyncSession, candidate_id: int) -> CandidateEntity | None:
    result = await db.execute(select(CandidateEntity).where(CandidateEntity.id == candidate_id))
    return result.scalar_one_or_none()


async def list_candidates(db: AsyncSession) -> list[CandidateEntity]:
    result = await db.execute(select(CandidateEntity).order_by(CandidateEntity.id.desc()))
    return list(result.scalars().all())


async def hr_view_profiles(
    db: AsyncSession, page_number: int, page_size: int, role: int | None, search: str | None
) -> PageResult:
    """Mirrors CandidateController::hrViewProfiles: users with role in [Employee, Candidate].
    EMPLOYEE was retired from the Role enum; TEAM_MEMBER is the functional equivalent
    (it's already the default role assigned to onboarded users elsewhere)."""
    stmt = select(UserEntity).where(UserEntity.role.in_([Role.TEAM_MEMBER, Role.CANDIDATE]))
    if role:
        stmt = stmt.where(UserEntity.role == role)
    if search:
        stmt = stmt.where(or_(UserEntity.name.ilike(f"%{search}%"), UserEntity.email.ilike(f"%{search}%")))
    stmt = stmt.order_by(UserEntity.id.desc())
    return await paginate(db, stmt, page_number, page_size)
