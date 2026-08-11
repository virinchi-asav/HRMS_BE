from datetime import date, datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import BigIntPK, HrmsBase


class TrainingStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class DayEntryStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    RESCHEDULED = "RESCHEDULED"


class MaterialType(str, Enum):
    LINK = "LINK"
    DOCUMENT = "DOCUMENT"


class AssessmentStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AssessmentGivenBy(str, Enum):
    """Who gives the per-trainee assessment for a training with has_assessment=True.
    TRAINER: the existing project-review flow (TrainingAssessmentEntity below).
    HR: HR builds a question-bank Task Assessment (app.hrms.models.task_assessment)
    for each trainee, only once the training is COMPLETED. Mutually exclusive - a
    training's trainer can't also give the old-style assessment when HR is selected,
    and vice versa (enforced in the service layer)."""

    TRAINER = "TRAINER"
    HR = "HR"


class TrainingProgramEntity(HrmsBase):
    __tablename__ = "training_programs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Logically a FK to the KMS module's mks_kms_account (a separate declarative
    # Base/engine) - stored as a plain int and resolved by name in the service layer,
    # same pattern as users.kms_department_id.
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trainer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    bu_head_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TrainingStatus.PENDING_APPROVAL.value)
    has_assessment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Only meaningful when has_assessment=True; null for has_assessment=False and for
    # legacy rows created before this field existed (treated as TRAINER, the prior
    # only behavior, wherever it's read).
    assessment_given_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingTraineeEntity(HrmsBase):
    __tablename__ = "training_trainees"
    __table_args__ = (UniqueConstraint("training_id", "trainee_id", name="uq_training_trainee"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    training_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=False)
    trainee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)


class TrainingDayEntryEntity(HrmsBase):
    __tablename__ = "training_day_entries"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    training_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    topic_covered: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingCommentEntity(HrmsBase):
    __tablename__ = "training_comments"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    training_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingMaterialEntity(HrmsBase):
    """A reference link or uploaded document the Trainer attaches so Trainees can view
    it. Exactly one of link_url/file_path is set, matching material_type."""

    __tablename__ = "training_materials"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    training_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=False)
    material_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Bare stored filename (not a full path) - same convention as file_storage_service's
    # other uploads; the owning training_id gives us the directory.
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    added_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingAssessmentEntity(HrmsBase):
    """One per (training, trainee) - each Trainee gets their own distinct assessment
    from the Trainer, not a single shared one for the whole training."""

    __tablename__ = "training_assessments"
    __table_args__ = (UniqueConstraint("training_id", "trainee_id", name="uq_training_assessment_trainee"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    training_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=False)
    trainee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detail_document_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=AssessmentStatus.PENDING.value)
    github_repo_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    project_zip_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingAssessmentScreenshotEntity(HrmsBase):
    __tablename__ = "training_assessment_screenshots"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_assessments.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
