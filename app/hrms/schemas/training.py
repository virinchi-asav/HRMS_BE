from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.hrms.models.training import AssessmentGivenBy, AssessmentStatus, DayEntryStatus


class TrainingCreateRequest(BaseModel):
    topic: str
    description: str | None = None
    account_id: int | None = None
    trainer_ids: list[int]
    trainee_ids: list[int]
    bu_head_id: int
    start_date: date
    end_date: date
    has_assessment: bool = False
    # Who gives the assessment when has_assessment=True - "TRAINER" (existing
    # project-review flow) or "HR" (question-bank Task Assessment, only once the
    # training is completed). Ignored/nulled when has_assessment=False.
    assessment_given_by: str | None = None

    @field_validator("assessment_given_by")
    @classmethod
    def _validate_assessment_given_by(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {g.value for g in AssessmentGivenBy}
        if v not in valid:
            raise ValueError(f"assessment_given_by must be one of {sorted(valid)}")
        return v


class RecordingCreateRequest(BaseModel):
    title: str | None = None
    link_url: str


class RejectRequest(BaseModel):
    reason: str | None = None


class DayEntryCreateRequest(BaseModel):
    entry_date: date
    topic_covered: str
    status: str

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        valid = {s.value for s in DayEntryStatus}
        if v not in valid:
            raise ValueError(f"status must be one of {sorted(valid)}")
        return v


class CommentCreateRequest(BaseModel):
    comment: str


class MaterialLinkCreateRequest(BaseModel):
    title: str
    link_url: str


class TraineeInfo(BaseModel):
    id: int
    name: str


class TrainerInfo(BaseModel):
    id: int
    name: str


class TrainingListItem(BaseModel):
    id: int
    topic: str
    account: str | None = None
    # Deprecated - kept for backward compatibility, populated as the first trainer.
    # Prefer trainer_ids/trainer_names, which reflect all trainers on this training.
    trainer_id: int
    trainer_name: str
    trainer_ids: list[int]
    trainer_names: list[str]
    bu_head_id: int
    bu_head_name: str
    status: str
    has_assessment: bool
    start_date: date
    end_date: date
    trainee_count: int


class TrainingResponse(BaseModel):
    id: int
    topic: str
    description: str | None = None
    account_id: int | None = None
    account: str | None = None
    # Deprecated - kept for backward compatibility, populated as the first trainer.
    # Prefer trainers, which reflects all trainers on this training.
    trainer_id: int
    trainer_name: str
    trainers: list[TrainerInfo]
    bu_head_id: int
    bu_head_name: str
    status: str
    has_assessment: bool
    assessment_given_by: str | None = None
    rejection_reason: str | None = None
    start_date: date
    end_date: date
    created_by: int
    created_by_name: str
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    trainees: list[TraineeInfo]


class DayEntryResponse(BaseModel):
    id: int
    training_id: int
    entry_date: date
    topic_covered: str
    status: str
    created_by: int
    created_by_name: str
    created_at: datetime | None = None


class CommentResponse(BaseModel):
    id: int
    training_id: int
    author_id: int
    author_name: str
    comment: str
    created_at: datetime | None = None


class MaterialResponse(BaseModel):
    id: int
    training_id: int
    material_type: str
    title: str
    link_url: str | None = None
    file_url: str | None = None
    added_by: int
    added_by_name: str
    created_at: datetime | None = None


class RecordingResponse(BaseModel):
    id: int
    training_id: int
    title: str | None = None
    link_url: str
    added_by: int
    added_by_name: str
    created_at: datetime | None = None


class AssessmentSubmissionUpdateRequest(BaseModel):
    """Trainee self-service update - both fields optional/independent so the Trainee
    can update the repo link and/or move the status without resending everything."""

    github_repo_url: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {AssessmentStatus.PENDING.value, AssessmentStatus.IN_PROGRESS.value, AssessmentStatus.READY_FOR_REVIEW.value}
        if v not in valid:
            raise ValueError(f"status must be one of {sorted(valid)}")
        return v


class AssessmentReviewRequest(BaseModel):
    marks: int
    status: str

    @field_validator("marks")
    @classmethod
    def _validate_marks(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("marks must be between 0 and 100")
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        valid = {AssessmentStatus.SUCCESS.value, AssessmentStatus.FAILURE.value}
        if v not in valid:
            raise ValueError(f"status must be one of {sorted(valid)}")
        return v


class ScreenshotResponse(BaseModel):
    id: int
    file_url: str
    created_at: datetime | None = None


class AssessmentResponse(BaseModel):
    id: int
    training_id: int
    trainee_id: int
    trainee_name: str
    description: str
    detail_document_url: str | None = None
    status: str
    github_repo_url: str | None = None
    project_zip_url: str | None = None
    marks: int | None = None
    reviewed_by: int | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    created_by: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    screenshots: list[ScreenshotResponse]
