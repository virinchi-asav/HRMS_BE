from datetime import datetime

from pydantic import BaseModel


class JobUpsertRequest(BaseModel):
    job_title: str
    experience_from: int | None = None
    experience_to: int | None = None
    employment_type: str
    location: str
    department: str
    edu_qualification: str
    key_skills: str
    job_description: str


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_title: str
    experience_from: int | None = None
    experience_to: int | None = None
    employment_type: str
    location: str
    department: str
    edu_qualification: str
    key_skills: str
    job_description: str
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
