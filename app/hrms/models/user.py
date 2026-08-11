from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.hrms.db import BigIntPK, HrmsBase


class UserEntity(HrmsBase):
    """Mirrors the live `users` table exactly (from postgres_complete.sql), which is
    considerably wider than the Laravel migrations alone suggest - many fields here
    (document uploads, training/onboarding fields, project-allocation fields) had no
    corresponding migration file but are confirmed present in the real schema.

    role: 1=Admin, 2=(unlabeled in the source app), 3=Employee, 4=Candidate,
    5=Manager/Team Lead, 6=Team Member (default), 7=BU Head.
    reporting_to/bu_head/reporting_manager store an employee-id-formatted STRING
    (e.g. "MKS/00003"), not a raw users.id integer - Laravel resolved these via regex,
    not a real FK, so no relationship is modeled on them here (see user_service for the
    equivalent lookup helper). Only `reviewed_by` is a genuine users.id self-reference.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    fields_to_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- KMS module access (single-login unification) ---
    # KMS role itself is derived from `role` via HRMS_TO_KMS_ROLE, not stored here; these
    # 3 fields are just the per-user content-visibility scoping the KMS module needs
    # (which department/account/user-type this person's KMS access is restricted to).
    # Logically FKs to mks_kms_department/mks_kms_account/mks_lms_user_type (tables
    # owned by the KMS module's own declarative Base/metadata) - the live DB has real
    # FOREIGN KEY constraints for these (added directly via SQL), but no `ForeignKey(...)`
    # is declared here since HrmsBase and the KMS Base are two separate SQLAlchemy
    # metadata registries; a cross-metadata FK can't be resolved by `create_all()`
    # against either engine alone (e.g. the test suite's two separate SQLite DBs).
    kms_department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kms_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kms_user_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remember_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Identity / employment basics ---
    employee_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    added_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    onboarding_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile_phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    personal_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modified_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modified_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    work_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skillset: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporting_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_of_hire: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seating_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    band: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_joining: Mapped[date | None] = mapped_column(nullable=True)
    employee_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    probation_end_date: Mapped[date | None] = mapped_column(nullable=True)
    probation_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_rating: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Personal / address ---
    present_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    father_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(nullable=True)
    gender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wedding_day: Mapped[date | None] = mapped_column(nullable=True)
    citizenship: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pan_card_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aadhaar_card_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uan_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_person_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_person_relation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- Job details / free text ---
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ask_me_about: Mapped[str | None] = mapped_column(Text, nullable=True)
    about_me: Mapped[str | None] = mapped_column(Text, nullable=True)
    can_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- Education ---
    tenth_school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenth_board: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenth_field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenth_date_of_completion: Mapped[date | None] = mapped_column(nullable=True)
    twelfth_school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twelfth_board: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twelfth_field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twelfth_date_of_completion: Mapped[date | None] = mapped_column(nullable=True)
    graduation_school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_date_of_completion: Mapped[date | None] = mapped_column(nullable=True)
    post_graduation_school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    post_graduation_degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    post_graduation_field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    post_graduation_date_of_completion: Mapped[date | None] = mapped_column(nullable=True)

    # --- Uploaded documents (store on-disk relative paths, like the Laravel app did) ---
    passport_photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_cv: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aadhar_card: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pan_card: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marksheet_10th: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marksheet_12th: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sem_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_3: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_4: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_5: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_6: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_7: Mapped[str | None] = mapped_column(Text, nullable=True)
    sem_8: Mapped[str | None] = mapped_column(Text, nullable=True)
    pg_sem_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    pg_sem_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    pg_sem_3: Mapped[str | None] = mapped_column(Text, nullable=True)
    pg_sem_4: Mapped[str | None] = mapped_column(Text, nullable=True)
    consolidated_marksheet: Mapped[str | None] = mapped_column(Text, nullable=True)
    pg_consolidated_marksheet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Candidate / onboarding / training / project-allocation ---
    candidate_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_set: Mapped[str | None] = mapped_column(String(255), nullable=True)
    internship_start_date: Mapped[date | None] = mapped_column(nullable=True)
    internship_end_date: Mapped[date | None] = mapped_column(nullable=True)
    tentative_onboarding_date: Mapped[date | None] = mapped_column(nullable=True)
    mks_onboarding_date: Mapped[date | None] = mapped_column(nullable=True)
    training_mode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    training_plan: Mapped[str | None] = mapped_column(String(255), nullable=True)
    training_start_date: Mapped[date | None] = mapped_column(nullable=True)
    training_end_date: Mapped[date | None] = mapped_column(nullable=True)
    evaluation_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluation_date: Mapped[date | None] = mapped_column(nullable=True)
    assessment_score: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trainer_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allocation_date: Mapped[date | None] = mapped_column(nullable=True)
    account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bu_head: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporting_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)

    reviewer: Mapped["UserEntity | None"] = relationship(remote_side=[id], lazy="selectin")
    skills: Mapped[list["SkillEntity"]] = relationship(lazy="selectin", foreign_keys="SkillEntity.user_id")
