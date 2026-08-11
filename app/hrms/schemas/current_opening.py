from datetime import datetime

from pydantic import BaseModel


class CurrentOpeningUpsertRequest(BaseModel):
    job_title: str
    description: str | None = None
    skills: list[str]
    account: str | None = None
    department: str | None = None
    status: str | None = None
    notes: str | None = None


class CurrentOpeningResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_title: str
    description: str | None = None
    skills: list[str]
    account: str | None = None
    department: str | None = None
    status: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
