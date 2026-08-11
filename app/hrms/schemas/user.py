from datetime import date, datetime

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.hrms.core.constants import HRMS_TO_KMS_ROLE, Role


def _validate_role(value: int | None) -> int | None:
    if value is not None:
        try:
            Role(value)
        except ValueError:
            raise ValueError(f"{value} is not a valid role") from None
    return value


class UserResponse(BaseModel):
    """Every user-facing field except `password`/`remember_token` (never serialized)."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    email: str
    status: str | None = None
    fields_to_update: str | None = None
    admin_message: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    role: int
    can_update: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # --- KMS module access (single-login unification) ---
    kms_department_id: int | None = None
    kms_account_id: int | None = None
    kms_user_type_id: int | None = None
    kms_role: str = ""

    @model_validator(mode="after")
    def _compute_kms_role(self) -> "UserResponse":
        try:
            self.kms_role = HRMS_TO_KMS_ROLE[Role(self.role)].value
        except ValueError:
            self.kms_role = ""
        return self

    employee_id: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    onboarding_status: str | None = None
    mobile_phone: str | None = None
    personal_email: str | None = None
    work_location: str | None = None
    project_name: str | None = None
    skillset: str | None = None
    reporting_to: str | None = None
    source_of_hire: str | None = None
    seating_location: str | None = None
    job_role: str | None = None
    total_experience: str | None = None
    experience: str | None = None
    band: str | None = None
    department: str | None = None
    job_title: str | None = None
    date_of_joining: date | None = None
    employee_experience: int | None = None
    probation_end_date: date | None = None
    probation_status: str | None = None
    employee_type: str | None = None
    employee_status: str | None = None
    work_phone: str | None = None
    extension: str | None = None
    final_rating: str | None = None

    present_address: str | None = None
    father_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    marital_status: str | None = None
    wedding_day: date | None = None
    citizenship: str | None = None
    permanent_address: str | None = None
    blood_group: str | None = None
    age: int | None = None
    pan_card_number: str | None = None
    aadhaar_card_number: str | None = None
    passport_number: str | None = None
    uan_number: str | None = None
    emergency_contact_person_name: str | None = None
    emergency_contact_number: str | None = None
    emergency_contact_person_relation: str | None = None

    job_description: str | None = None
    ask_me_about: str | None = None
    about_me: str | None = None

    tenth_school_name: str | None = None
    tenth_board: str | None = None
    tenth_field_of_study: str | None = None
    tenth_date_of_completion: date | None = None
    twelfth_school_name: str | None = None
    twelfth_board: str | None = None
    twelfth_field_of_study: str | None = None
    twelfth_date_of_completion: date | None = None
    graduation_school_name: str | None = None
    graduation_degree: str | None = None
    graduation_field_of_study: str | None = None
    graduation_date_of_completion: date | None = None
    post_graduation_school_name: str | None = None
    post_graduation_degree: str | None = None
    post_graduation_field_of_study: str | None = None
    post_graduation_date_of_completion: date | None = None

    passport_photo: str | None = None
    latest_cv: str | None = None
    aadhar_card: str | None = None
    pan_card: str | None = None
    marksheet_10th: str | None = None
    marksheet_12th: str | None = None
    sem_1: str | None = None
    sem_2: str | None = None
    sem_3: str | None = None
    sem_4: str | None = None
    sem_5: str | None = None
    sem_6: str | None = None
    sem_7: str | None = None
    sem_8: str | None = None
    pg_sem_1: str | None = None
    pg_sem_2: str | None = None
    pg_sem_3: str | None = None
    pg_sem_4: str | None = None
    consolidated_marksheet: str | None = None
    pg_consolidated_marksheet: str | None = None

    candidate_type: str | None = None
    skill_set: str | None = None
    internship_start_date: date | None = None
    internship_end_date: date | None = None
    tentative_onboarding_date: date | None = None
    mks_onboarding_date: date | None = None
    training_mode: str | None = None
    training_plan: str | None = None
    training_start_date: date | None = None
    training_end_date: date | None = None
    evaluation_type: str | None = None
    evaluation_date: date | None = None
    assessment_score: str | None = None
    trainer_notes: str | None = None
    allocation_date: date | None = None
    account: str | None = None
    bu_head: str | None = None
    reporting_manager: str | None = None


class UserListItem(BaseModel):
    """Slim shape for admin user-list tables.

    `department` is the free-text HRMS org/department field; `kms_department` is the
    resolved name of the *KMS module's* structured department (kms_department_id, set
    via the "KMS Access" section of the profile editor) - a different concept, kept as
    a separate field rather than conflated with `department` to avoid ambiguity.
    """

    model_config = {"from_attributes": True}

    id: int
    name: str
    email: str
    role: int
    employee_id: str | None = None
    department: str | None = None
    employee_status: str | None = None
    kms_department_id: int | None = None
    kms_department: str | None = None


class UserCreateRequest(BaseModel):
    """Admin quick-create (UserController::store) - a Welcome email + default password
    is issued; full profile details are filled in later via UserProfileUpdateRequest."""

    name: str
    email: EmailStr
    role: int

    _validate_role = field_validator("role")(_validate_role)


class UserAdminUpdateRequest(BaseModel):
    """Admin quick-edit (UserController::update) - partial update of the basics."""

    name: str | None = None
    email: EmailStr | None = None
    role: int | None = None
    password: str | None = None

    _validate_role = field_validator("role")(_validate_role)


class UserProfileUpdateRequest(BaseModel):
    """The large combined self-service + HR profile edit form
    (UserController::updateProfile / updateUserProfile). All fields optional - only
    supplied fields are changed. File fields (passport_photo, latest_cv, etc.) are
    handled as separate UploadFile parameters in the router, not here."""

    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: int | None = None

    _validate_role = field_validator("role")(_validate_role)

    # --- KMS module access (admin-only, see ADMIN_ONLY_PROFILE_FIELDS) ---
    kms_department_id: int | None = None
    kms_account_id: int | None = None
    kms_user_type_id: int | None = None

    employee_id: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    onboarding_status: str | None = None
    mobile_phone: str | None = None
    personal_email: str | None = None
    work_location: str | None = None
    project_name: str | None = None
    skillset: str | None = None
    reporting_to: str | None = None
    source_of_hire: str | None = None
    seating_location: str | None = None
    job_role: str | None = None
    total_experience: str | None = None
    experience: str | None = None
    band: str | None = None
    department: str | None = None
    job_title: str | None = None
    date_of_joining: date | None = None
    employee_experience: int | None = None
    probation_end_date: date | None = None
    probation_status: str | None = None
    employee_type: str | None = None
    employee_status: str | None = None
    work_phone: str | None = None
    extension: str | None = None
    final_rating: str | None = None

    present_address: str | None = None
    father_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    marital_status: str | None = None
    wedding_day: date | None = None
    citizenship: str | None = None
    permanent_address: str | None = None
    blood_group: str | None = None
    age: int | None = None
    pan_card_number: str | None = None
    aadhaar_card_number: str | None = None
    passport_number: str | None = None
    uan_number: str | None = None
    emergency_contact_person_name: str | None = None
    emergency_contact_number: str | None = None
    emergency_contact_person_relation: str | None = None

    job_description: str | None = None
    ask_me_about: str | None = None
    about_me: str | None = None

    tenth_school_name: str | None = None
    tenth_board: str | None = None
    tenth_field_of_study: str | None = None
    tenth_date_of_completion: date | None = None
    twelfth_school_name: str | None = None
    twelfth_board: str | None = None
    twelfth_field_of_study: str | None = None
    twelfth_date_of_completion: date | None = None
    graduation_school_name: str | None = None
    graduation_degree: str | None = None
    graduation_field_of_study: str | None = None
    graduation_date_of_completion: date | None = None
    post_graduation_school_name: str | None = None
    post_graduation_degree: str | None = None
    post_graduation_field_of_study: str | None = None
    post_graduation_date_of_completion: date | None = None

    candidate_type: str | None = None
    skill_set: str | None = None
    internship_start_date: date | None = None
    internship_end_date: date | None = None
    tentative_onboarding_date: date | None = None
    mks_onboarding_date: date | None = None
    training_mode: str | None = None
    training_plan: str | None = None
    training_start_date: date | None = None
    training_end_date: date | None = None
    evaluation_type: str | None = None
    evaluation_date: date | None = None
    assessment_score: str | None = None
    trainer_notes: str | None = None
    allocation_date: date | None = None
    account: str | None = None
    bu_head: str | None = None
    reporting_manager: str | None = None


class ProfileReviewRequest(BaseModel):
    admin_message: str | None = None
    status: str  # "reviewed_accepted" | "needs_update"
