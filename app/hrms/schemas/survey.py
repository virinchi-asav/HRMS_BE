from datetime import datetime

from pydantic import BaseModel


class SurveySubmissionRequest(BaseModel):
    client_id: int
    delivery: int
    quality: int
    expertise: int
    mksvalues: int
    overallservicesatisfaction: int
    comments: str | None = None


class SurveyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    customer_id: int
    delivery: int
    quality: int
    expertise: int
    mksvalues: int
    overallservicesatisfaction: int
    comments: str | None = None
    created_at: datetime | None = None
