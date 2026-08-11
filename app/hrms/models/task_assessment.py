from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import BigIntPK, HrmsBase


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"
    FILL_IN_BLANK = "FILL_IN_BLANK"
    ENTER_ANSWER = "ENTER_ANSWER"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AssigneeStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"


class DifficultyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class QuestionMode(str, Enum):
    """MANUAL: HR hand-picks question_ids at task creation - one shared, fixed
    TaskQuestionEntity snapshot for every assignee (assignee_id left null on those rows).
    RANDOM: HR instead picks a source bank (+ optional module) and a count from
    ALLOWED_RANDOM_COUNTS - each assignee gets their own independent random draw,
    snapshotted the first time THAT attempt is started (see
    task_assessment_service._snapshot_random_questions), so a retake also gets a fresh
    draw. Those TaskQuestionEntity rows carry assignee_id set to the owning attempt."""

    MANUAL = "MANUAL"
    RANDOM = "RANDOM"


class QuestionBankEntity(HrmsBase):
    """A reusable, org-wide library of questions - any HR/Trainer (Admin, HR, or a
    TEAM_MEMBER acting as Trainer) can read/reuse any bank; only the creator (or
    Admin/HR) can edit/archive it, enforced in the service layer.

    account_id/custom_account_type capture which Account Type (the KMS module's
    mks_kms_account - the same "Account Type" used on Training) this bank's content is
    intended for - mutually exclusive, exactly one may be set: account_id references an
    existing KMS account (plain int, resolved by name in the service layer, same
    cross-metadata convention as TrainingProgramEntity.account_id); custom_account_type
    is a one-off freeform label used only when the author picks "Other" instead of an
    existing account, without creating a real KMS account row. Both may be null
    (account type left unspecified)."""

    __tablename__ = "task_question_banks"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_account_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BankQuestionEntity(HrmsBase):
    """module_name is a free-text label (not linked to any Category/Training table).
    correct_answer_text holds the marked answer for TRUE_FALSE/FILL_IN_BLANK/ENTER_ANSWER
    (graded by case-insensitive trimmed string equality); MULTIPLE_CHOICE instead marks
    correctness on its BankQuestionOptionEntity rows and leaves this column null."""

    __tablename__ = "task_question_bank_questions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    bank_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_question_banks.id"), nullable=False)
    module_name: Mapped[str] = mapped_column(String(255), nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    correct_answer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BankQuestionOptionEntity(HrmsBase):
    """MCQ options only - one row is flagged is_correct=True per question."""

    __tablename__ = "task_question_bank_question_options"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    question_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_question_bank_questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TaskEntity(HrmsBase):
    """A timed assignment built from hand-picked bank questions, fully snapshotted onto
    TaskQuestionEntity/TaskQuestionOptionEntity at creation time - later edits/archival
    of the source bank questions never affect an already-created task. No bank_id FK
    here since a task's question_ids can span multiple banks.

    training_id links this task back to a specific Training whose assessment_given_by
    was set to HR (app.hrms.models.training) - null for every other, standalone task."""

    __tablename__ = "task_assessment_tasks"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=True)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskStatus.OPEN.value)
    # Default 3 attempts per trainee before they're locked out and HR must reassign (see
    # TaskAssigneeEntity.max_attempts, which copies this value forward per-attempt so HR
    # can grant a specific trainee extra attempts without affecting anyone else assigned
    # to this same task).
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    question_mode: Mapped[str] = mapped_column(String(20), nullable=False, default=QuestionMode.MANUAL.value)
    # Only set when question_mode == RANDOM - the bank (+ optional module filter) each
    # assignee's questions are independently drawn from, and how many to draw.
    source_bank_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("task_question_banks.id"), nullable=True)
    source_module_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    random_question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # When skill_name is set, a passing attempt on this task auto-logs (or upgrades) that
    # skill on the trainee's Skills module profile - see task_assessment_service's
    # DIFFICULTY_TO_RATING mapping and skill_service.auto_log_skill_from_task_pass.
    difficulty_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    skill_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skill_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskQuestionEntity(HrmsBase):
    """A frozen copy of one bank question. correct_answer_text is never serialized to a
    trainee mid-attempt.

    For a MANUAL-mode task, assignee_id is null and this row is a shared snapshot taken
    at task-creation time (one set of rows per task_id, used by every assignee). For a
    RANDOM-mode task, assignee_id is set to the specific TaskAssigneeEntity (attempt)
    this row was randomly drawn for - see QuestionMode and
    task_assessment_service._snapshot_random_questions."""

    __tablename__ = "task_assessment_task_questions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_assessment_tasks.id"), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_assessment_assignees.id"), nullable=True
    )
    source_question_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_question_bank_questions.id"), nullable=True
    )
    module_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskQuestionOptionEntity(HrmsBase):
    """A frozen copy of one bank question option. is_correct is never serialized to a
    trainee mid-attempt."""

    __tablename__ = "task_assessment_task_question_options"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    task_question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_assessment_task_questions.id"), nullable=False
    )
    option_text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TaskAssigneeEntity(HrmsBase):
    """One row per attempt - a trainee can accumulate several rows for the same
    (task_id, trainee_id) over retries/reassignment, so this is no longer "the" attempt,
    just one of them; callers should read the latest (highest attempt_number) row for a
    trainee's current state. deadline_at is computed once at start_or_resume time
    (started_at + task.time_limit_minutes) and frozen from then on, even if the task's
    time_limit_minutes is edited later.

    attempt_number starts at 1 and only ever increases (never reused), so the unique
    constraint never collides even across a trainee-initiated retry or an HR reassign.
    max_attempts is copied forward from task.max_attempts onto each new row and is what
    actually caps this trainee: a trainee-initiated retry (task_assessment_service.
    retry_task) copies it unchanged, while an HR reassign (reassign_task) bumps it by
    another +task.max_attempts - so raising the cap for one locked-out trainee never
    affects anyone else assigned to the same task.

    submit_reason records why the last submit happened (e.g. "TAB_SWITCH" for the
    anti-cheat auto-submit versus null for a normal/trainee-initiated submit or a
    server-side timeout) - purely informational, shown to HR in reports."""

    __tablename__ = "task_assessment_assignees"
    __table_args__ = (UniqueConstraint("task_id", "trainee_id", "attempt_number", name="uq_task_assignee_trainee_attempt"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_assessment_tasks.id"), nullable=False)
    trainee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssigneeStatus.NOT_STARTED.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submit_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    marks_obtained: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_marks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskAnswerEntity(HrmsBase):
    """One row per (assignee, task_question) - the unique constraint makes autosave an
    idempotent upsert. is_correct/marks_awarded are graded immediately at each autosave
    (not deferred to submit) so finalize just sums already-graded rows."""

    __tablename__ = "task_assessment_answers"
    __table_args__ = (UniqueConstraint("assignee_id", "task_question_id", name="uq_task_answer_assignee_question"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    assignee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_assessment_assignees.id"), nullable=False)
    task_question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_assessment_task_questions.id"), nullable=False
    )
    selected_option_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_assessment_task_question_options.id"), nullable=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    marks_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
