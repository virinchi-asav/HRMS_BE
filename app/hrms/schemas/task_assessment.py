from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from app.hrms.models.task_assessment import DifficultyLevel, QuestionMode, QuestionType

QUESTION_TYPE_VALUES = {t.value for t in QuestionType}
DIFFICULTY_LEVEL_VALUES = {d.value for d in DifficultyLevel}
QUESTION_MODE_VALUES = {m.value for m in QuestionMode}
# The fixed set of counts HR can pick from when allocating a random draw out of a large
# (100+) question bank - see task_assessment_service._snapshot_random_questions.
ALLOWED_RANDOM_COUNTS = {10, 15, 20, 25, 50}
SUBMIT_REASON_VALUES = {"TAB_SWITCH"}


# ---- Question banks ----


class BankCreateRequest(BaseModel):
    name: str
    description: str | None = None
    # Which Account Type this bank's content is for - at most one of the two may be
    # set: account_id references an existing KMS account, custom_account_type is a
    # one-off freeform label used only when "Other" is picked instead. Both null means
    # unspecified.
    account_id: int | None = None
    custom_account_type: str | None = None

    @model_validator(mode="after")
    def _validate_account_type(self) -> "BankCreateRequest":
        if self.account_id is not None and self.custom_account_type is not None:
            raise ValueError("Pick either an existing Account Type or 'Other', not both")
        return self


class BankUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    account_id: int | None = None
    custom_account_type: str | None = None

    @model_validator(mode="after")
    def _validate_account_type(self) -> "BankUpdateRequest":
        if self.account_id is not None and self.custom_account_type is not None:
            raise ValueError("Pick either an existing Account Type or 'Other', not both")
        return self


class BankResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    account_id: int | None = None
    account_name: str | None = None
    custom_account_type: str | None = None
    is_active: bool
    created_by: int
    created_by_name: str
    question_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---- Bank questions ----


class OptionInput(BaseModel):
    option_text: str
    is_correct: bool = False


class BankQuestionCreateRequest(BaseModel):
    module_name: str
    question_type: str
    question_text: str
    marks: int = 1
    correct_answer_text: str | None = None
    options: list[OptionInput] = []

    @field_validator("question_type")
    @classmethod
    def _validate_question_type(cls, v: str) -> str:
        if v not in QUESTION_TYPE_VALUES:
            raise ValueError(f"question_type must be one of {sorted(QUESTION_TYPE_VALUES)}")
        return v

    @field_validator("marks")
    @classmethod
    def _validate_marks(cls, v: int) -> int:
        if v < 1:
            raise ValueError("marks must be at least 1")
        return v

    @model_validator(mode="after")
    def _validate_answer_shape(self) -> "BankQuestionCreateRequest":
        if self.question_type == QuestionType.MULTIPLE_CHOICE.value:
            if len(self.options) < 2:
                raise ValueError("MULTIPLE_CHOICE questions need at least 2 options")
            if sum(1 for o in self.options if o.is_correct) != 1:
                raise ValueError("MULTIPLE_CHOICE questions need exactly one correct option")
            if self.correct_answer_text is not None:
                raise ValueError("correct_answer_text must not be set for MULTIPLE_CHOICE")
        else:
            if self.options:
                raise ValueError("options must be empty for non-MULTIPLE_CHOICE questions")
            if not self.correct_answer_text or not self.correct_answer_text.strip():
                raise ValueError("correct_answer_text is required for non-MULTIPLE_CHOICE questions")
        return self


class BankQuestionUpdateRequest(BankQuestionCreateRequest):
    """Full-replace update - same shape/validators as create; MCQ options are deleted
    and recreated from this payload rather than diffed."""


class OptionResponse(BaseModel):
    id: int
    option_text: str
    is_correct: bool
    display_order: int


class BankQuestionResponse(BaseModel):
    id: int
    bank_id: int
    module_name: str
    question_type: str
    question_text: str
    marks: int
    correct_answer_text: str | None = None
    is_active: bool
    options: list[OptionResponse]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BankQuestionImportError(BaseModel):
    row: int
    message: str


class BankQuestionImportResponse(BaseModel):
    created: int
    errors: list[BankQuestionImportError]


# ---- Task creation / assignment ----


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    # Set only when this task IS the HR-given assessment for a specific Training (whose
    # assessment_given_by must be "HR" and status must be COMPLETED) - null for every
    # other, standalone task. Validated in the service layer.
    training_id: int | None = None
    time_limit_minutes: int
    pass_percentage: int = 40
    # Default 3 attempts before a trainee locks out and needs HR to reassign them - see
    # TaskAssigneeEntity.max_attempts.
    max_attempts: int = 3
    # MANUAL: question_ids is the hand-picked, fixed set shared by every assignee (as
    # before). RANDOM: question_ids must be empty instead - source_bank_id (+ optional
    # source_module_name) and random_question_count (one of ALLOWED_RANDOM_COUNTS) drive
    # an independent random draw per assignee, taken when each attempt starts.
    question_mode: str = QuestionMode.MANUAL.value
    question_ids: list[int] = []
    source_bank_id: int | None = None
    source_module_name: str | None = None
    random_question_count: int | None = None
    trainee_ids: list[int] = []
    # When skill_name is set, a passing attempt on this task auto-logs (or upgrades)
    # that skill on the trainee's Skills module profile, rated per difficulty_level -
    # see task_assessment_service.DIFFICULTY_TO_RATING. Leave skill_name unset for a
    # task that isn't meant to feed the Skills module.
    difficulty_level: str | None = None
    skill_name: str | None = None
    skill_category: str | None = None

    @field_validator("difficulty_level")
    @classmethod
    def _validate_difficulty_level(cls, v: str | None) -> str | None:
        if v is not None and v not in DIFFICULTY_LEVEL_VALUES:
            raise ValueError(f"difficulty_level must be one of {sorted(DIFFICULTY_LEVEL_VALUES)}")
        return v

    @field_validator("time_limit_minutes")
    @classmethod
    def _validate_time_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("time_limit_minutes must be greater than 0")
        return v

    @field_validator("pass_percentage")
    @classmethod
    def _validate_pass_percentage(cls, v: int) -> int:
        if not (0 < v <= 100):
            raise ValueError("pass_percentage must be between 1 and 100")
        return v

    @field_validator("max_attempts")
    @classmethod
    def _validate_max_attempts(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_attempts must be at least 1")
        return v

    @field_validator("question_mode")
    @classmethod
    def _validate_question_mode(cls, v: str) -> str:
        if v not in QUESTION_MODE_VALUES:
            raise ValueError(f"question_mode must be one of {sorted(QUESTION_MODE_VALUES)}")
        return v

    @field_validator("question_ids")
    @classmethod
    def _validate_question_ids(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("question_ids must not contain duplicates")
        return v

    @model_validator(mode="after")
    def _validate_question_source(self) -> "TaskCreateRequest":
        if self.question_mode == QuestionMode.RANDOM.value:
            if self.question_ids:
                raise ValueError("question_ids must be empty when question_mode is RANDOM")
            if self.source_bank_id is None:
                raise ValueError("source_bank_id is required when question_mode is RANDOM")
            if self.random_question_count not in ALLOWED_RANDOM_COUNTS:
                raise ValueError(f"random_question_count must be one of {sorted(ALLOWED_RANDOM_COUNTS)}")
        else:
            if not self.question_ids:
                raise ValueError("At least one question is required")
            if self.source_bank_id is not None or self.random_question_count is not None or self.source_module_name is not None:
                raise ValueError(
                    "source_bank_id/source_module_name/random_question_count must not be set when question_mode is MANUAL"
                )
        return self


class AssignTraineesRequest(BaseModel):
    trainee_ids: list[int]

    @field_validator("trainee_ids")
    @classmethod
    def _validate_trainee_ids(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("At least one trainee is required")
        return v


class AssignByLocationRequest(BaseModel):
    work_location: str

    @field_validator("work_location")
    @classmethod
    def _validate_work_location(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("work_location is required")
        return v


class AnswerSaveRequest(BaseModel):
    selected_option_id: int | None = None
    answer_text: str | None = None


# ---- Task list / detail (management view - correct answers included) ----


class MyAssigneeSummary(BaseModel):
    id: int
    status: str
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    submitted_at: datetime | None = None
    percentage: float | None = None
    passed: bool | None = None
    attempt_number: int
    max_attempts: int
    can_retry: bool
    locked_out: bool


class TaskListItem(BaseModel):
    id: int
    title: str
    status: str
    training_id: int | None = None
    time_limit_minutes: int
    pass_percentage: int
    max_attempts: int
    question_mode: str
    difficulty_level: str | None = None
    skill_name: str | None = None
    skill_category: str | None = None
    created_by: int
    created_by_name: str
    question_count: int
    total_marks: int
    assignee_count: int
    submitted_count: int
    created_at: datetime | None = None
    my_assignee: MyAssigneeSummary | None = None


class TaskOptionManageItem(BaseModel):
    id: int
    option_text: str
    is_correct: bool
    display_order: int


class TaskQuestionManageItem(BaseModel):
    id: int
    module_name: str | None = None
    question_type: str
    question_text: str
    marks: int
    correct_answer_text: str | None = None
    display_order: int
    options: list[TaskOptionManageItem]


class TaskAssigneeSummary(BaseModel):
    id: int
    trainee_id: int
    trainee_name: str
    status: str
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    submitted_at: datetime | None = None
    submit_reason: str | None = None
    marks_obtained: int | None = None
    total_marks: int | None = None
    percentage: float | None = None
    passed: bool | None = None
    attempt_number: int
    max_attempts: int
    can_retry: bool
    locked_out: bool


class TaskManageDetailResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str
    training_id: int | None = None
    time_limit_minutes: int
    pass_percentage: int
    max_attempts: int
    # RANDOM-mode tasks have no single fixed question set (each assignee draws their
    # own) - questions is always empty and total_marks is 0 in that case; source_bank_id
    # /source_bank_name/source_module_name/random_question_count describe the draw
    # instead. Each assignee's own actual total_marks (post-draw) is on TaskAssigneeSummary.
    question_mode: str
    source_bank_id: int | None = None
    source_bank_name: str | None = None
    source_module_name: str | None = None
    random_question_count: int | None = None
    difficulty_level: str | None = None
    skill_name: str | None = None
    skill_category: str | None = None
    created_by: int
    created_by_name: str
    total_marks: int
    questions: list[TaskQuestionManageItem]
    assignees: list[TaskAssigneeSummary]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None


# ---- Task take (trainee view - correctness always redacted) ----


class TaskOptionTakeItem(BaseModel):
    id: int
    option_text: str
    display_order: int


class TaskQuestionTakeItem(BaseModel):
    id: int
    module_name: str | None = None
    question_type: str
    question_text: str
    marks: int
    display_order: int
    options: list[TaskOptionTakeItem] | None = None
    my_answer: str | None = None
    my_selected_option_id: int | None = None


class TaskTakeResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str
    time_limit_minutes: int
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    attempt_number: int
    max_attempts: int
    questions: list[TaskQuestionTakeItem]


class AnswerSaveResponse(BaseModel):
    task_question_id: int
    saved: bool


class SubmitTaskRequest(BaseModel):
    # Set by the trainee-facing anti-cheat handler when the assessment auto-submits
    # because the trainee switched tabs/minimized the window mid-attempt - null for a
    # normal, trainee-initiated submit. Purely informational (shown to HR); it does not
    # change how the attempt is graded.
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, v: str | None) -> str | None:
        if v is not None and v not in SUBMIT_REASON_VALUES:
            raise ValueError(f"reason must be one of {sorted(SUBMIT_REASON_VALUES)}")
        return v


class TaskResultResponse(BaseModel):
    task_id: int
    status: str
    marks_obtained: int | None = None
    total_marks: int | None = None
    percentage: float | None = None
    passed: bool | None = None
    submitted_at: datetime | None = None
    submit_reason: str | None = None
    attempt_number: int
    max_attempts: int
    can_retry: bool
    locked_out: bool


class RetryResponse(BaseModel):
    attempt_number: int
    max_attempts: int
    status: str


# ---- Report ----


class TaskReportRow(BaseModel):
    assignee_id: int
    trainee_id: int
    trainee_name: str
    status: str
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    submitted_at: datetime | None = None
    submit_reason: str | None = None
    marks_obtained: int | None = None
    total_marks: int | None = None
    percentage: float | None = None
    passed: bool | None = None
    attempt_number: int
    max_attempts: int
    locked_out: bool


class TaskReportResponse(BaseModel):
    task_id: int
    title: str
    pass_percentage: int
    assignee_count: int
    not_started_count: int
    in_progress_count: int
    submitted_count: int
    pass_count: int
    average_percentage: float | None = None
    rows: list[TaskReportRow]
