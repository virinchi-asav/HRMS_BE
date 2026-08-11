from datetime import date, datetime

from pydantic import BaseModel


class SubSkillUpsertRequest(BaseModel):
    """Field names follow the Laravel form's sub_skills.$i.* naming (sub_skill_name/
    sub_skill_category), which the service maps onto SubSkillEntity's skill_name/
    skill_category columns. Attachment file is a separate UploadFile in the router."""

    id: int | None = None  # existing sub-skill id, for update matching; None = new row
    sub_skill_name: str
    sub_skill_category: str
    rating: str
    level_of_proficiency: str | None = None
    project_exposure: bool | None = None
    experience: str | None = None
    active_in_the_project: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    account: str | None = None
    notes: str | None = None
    project_name: str | None = None
    no_skill_gap: bool | None = None
    remove_attachment: bool = False
    # Filename returned by POST /api/hrms/skills/attachments (upload_staged_attachment) -
    # None means "leave the existing attachment unchanged" unless remove_attachment=True.
    attachment: str | None = None


class SkillUpsertRequest(BaseModel):
    skill_name: str
    skill_category: str
    rating: str
    level_of_proficiency: str | None = None
    project_exposure: bool | None = None
    # Matches SkillEntity.experience being a real boolean column (unlike SubSkill's
    # free-text experience field) - see the model's docstring for why.
    experience: bool | None = None
    active_in_the_project: bool | None = None
    account: str
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    project_name: str | None = None
    no_skill_gap: bool | None = None
    remove_attachment: bool = False
    # Filename returned by POST /api/hrms/skills/attachments (upload_staged_attachment).
    attachment: str | None = None
    sub_skills: list[SubSkillUpsertRequest] = []


class SkillReviewRequest(BaseModel):
    """Manager-reviewing-a-reportee's-skill path (SkillController::update, branch A) -
    a narrower field set than the full owner-edit path."""

    start_date: date | None = None
    end_date: date | None = None
    account: str | None = None
    notes: str | None = None
    project_name: str | None = None
    no_skill_gap: bool | None = None
    sub_skills: list[SubSkillUpsertRequest] = []


class SubSkillResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    skill_id: str | None = None
    skill_name: str
    skill_category: str
    rating: str
    level_of_proficiency: str | None = None
    project_exposure: bool | None = None
    experience: str | None = None
    active_in_the_project: bool | None = None
    attachment: str | None = None
    mail_triggered: bool
    manager_rating: str | None = None
    skill_gap: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    account: str | None = None
    notes: str | None = None
    project_name: str | None = None
    no_skill_gap: bool | None = None


class SkillResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    skill_id: str | None = None
    user_id: int
    user_name: str | None = None
    skill_name: str
    skill_category: str
    rating: str
    level_of_proficiency: str | None = None
    project_exposure: bool | None = None
    experience: bool | None = None
    active_in_the_project: bool | None = None
    attachment: str | None = None
    mail_triggered: bool
    manager_rating: str | None = None
    skill_gap: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    account: str | None = None
    notes: str | None = None
    project_name: str | None = None
    no_skill_gap: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    sub_skills: list[SubSkillResponse] = []
