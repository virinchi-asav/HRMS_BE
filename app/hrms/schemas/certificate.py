from datetime import date, datetime

from pydantic import BaseModel


class CertificateTemplateResponse(BaseModel):
    id: int
    file_url: str
    uploaded_by: int
    uploaded_by_name: str
    created_at: datetime | None = None


class CertificateIssueRequest(BaseModel):
    trainee_id: int
    recipient_name: str
    issue_date: date


class CertificateResponse(BaseModel):
    id: int
    training_id: int
    trainee_id: int
    trainee_name: str
    recipient_name: str
    topic: str
    issue_date: date
    file_url: str
    issued_by: int
    issued_by_name: str
    created_at: datetime | None = None
