from datetime import datetime

from pydantic import BaseModel, EmailStr


class ClientUpsertRequest(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    organization: str


class ClientResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    firstname: str
    lastname: str
    email: str
    organization: str
    username: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
