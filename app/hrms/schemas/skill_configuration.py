from datetime import datetime

from pydantic import BaseModel


class SkillConfigurationUpsertRequest(BaseModel):
    skill_name: str
    skill_category: str
    department: str | None = None
    is_sub_skill_is_available: bool = False
    status: bool = False


class SkillConfigurationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    skill_name: str
    skill_category: str
    is_sub_skill_is_available: int | None = None
    status: int | None = None
    department: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
