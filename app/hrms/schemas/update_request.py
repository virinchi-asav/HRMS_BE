from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.hrms.schemas.user import UserListItem


class UpdateRequestCreate(BaseModel):
    reason: str | None = None


class UpdateRequestAction(BaseModel):
    action: Literal["approve", "reject"]
    admin_note: str | None = None


class UpdateRequestResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    status: str
    reason: str | None = None
    admin_note: str | None = None
    created_at: datetime | None = None
    user: UserListItem | None = None
