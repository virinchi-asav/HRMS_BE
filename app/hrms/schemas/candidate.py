from datetime import datetime

from pydantic import BaseModel, EmailStr


class CandidateApplyRequest(BaseModel):
    """Public job-application form (career-detail page). Resume file is a separate
    UploadFile parameter in the router, not part of this model."""

    job_id: int
    candidate_name: str
    candidate_number: int
    candidate_email: EmailStr
    candidate_address: str | None = None
    candidate_pin_code: str | None = None
    candidate_city: str | None = None
    candidate_state: str | None = None
    candidate_job_title: str | None = None
    candidate_experience_yrs: int | None = None
    candidate_experience_month: int | None = None
    candidate_employer: str | None = None
    candidate_location: str | None = None
    candidate_ctc: str | None = None
    candidate_expected_ctc: str | None = None
    candidate_doj: int


class CandidateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_id: int
    candidate_name: str
    candidate_number: int
    candidate_email: str
    candidate_address: str | None = None
    candidate_pin_code: str | None = None
    candidate_city: str | None = None
    candidate_state: str | None = None
    candidate_job_title: str | None = None
    candidate_experience_yrs: int | None = None
    candidate_experience_month: int | None = None
    candidate_employer: str | None = None
    candidate_location: str | None = None
    candidate_ctc: str | None = None
    candidate_expected_ctc: str | None = None
    candidate_doj: int
    candidate_resume: str
    created_at: datetime | None = None
