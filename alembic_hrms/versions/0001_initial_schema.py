"""initial schema for the mksvision_mkswebsite_new MySQL database - mirrors the schema
captured in postgres_complete.sql (a Postgres-syntax dump of what is actually a MySQL
database - the column/type analysis is authoritative, only the DDL dialect differs
here), plus a small number of deliberate additions (deleted_at on current_openings/
skills/skill_configurations to make their pre-existing "restore" routes actually work;
FKs the source Laravel app never declared at the DB level but always relied on at the
application level: candidates.job_id, clientsurvey.customer_id, skills.user_id,
sub_skills.skill_id-to-skills.skill_id, update_requests.user_id, profiles.user_id,
users.reviewed_by).

candidates.job_id, clientsurvey.customer_id, and skills.user_id are BigInteger here
(not the plain Integer their source columns actually were) to match the BigInteger
primary key they reference (jobs.id/clients.id/users.id, all BigIntPK) - MySQL 8 (unlike
Postgres, which tolerates the implicit widening cast) rejects an FK between mismatched
integer widths outright, so this migration could never actually complete on a fresh
MySQL 8 database without this fix.

Revision ID: 0001
Revises:
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("fields_to_update", sa.Text, nullable=True),
        sa.Column("admin_message", sa.Text, nullable=True),
        sa.Column("reviewed_by", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("email_verified_at", sa.DateTime, nullable=True),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("role", sa.Integer, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("remember_token", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("employee_id", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("middle_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("added_by", sa.Integer, nullable=True),
        sa.Column("added_time", sa.DateTime, nullable=True),
        sa.Column("onboarding_status", sa.String(255), nullable=True),
        sa.Column("mobile_phone", sa.String(255), nullable=True),
        sa.Column("personal_email", sa.String(255), nullable=True),
        sa.Column("modified_by", sa.Integer, nullable=True),
        sa.Column("modified_time", sa.DateTime, nullable=True),
        sa.Column("work_location", sa.String(255), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("skillset", sa.Text, nullable=True),
        sa.Column("reporting_to", sa.String(255), nullable=True),
        sa.Column("source_of_hire", sa.String(255), nullable=True),
        sa.Column("seating_location", sa.String(255), nullable=True),
        sa.Column("job_role", sa.String(255), nullable=True),
        sa.Column("total_experience", sa.Text, nullable=True),
        sa.Column("experience", sa.Text, nullable=True),
        sa.Column("band", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("date_of_joining", sa.Date, nullable=True),
        sa.Column("employee_experience", sa.Integer, nullable=True),
        sa.Column("probation_end_date", sa.Date, nullable=True),
        sa.Column("probation_status", sa.String(255), nullable=True),
        sa.Column("employee_type", sa.String(255), nullable=True),
        sa.Column("employee_status", sa.String(255), nullable=True),
        sa.Column("work_phone", sa.String(255), nullable=True),
        sa.Column("extension", sa.String(255), nullable=True),
        sa.Column("final_rating", sa.String(255), nullable=True),
        sa.Column("present_address", sa.Text, nullable=True),
        sa.Column("father_name", sa.String(255), nullable=True),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("gender", sa.String(255), nullable=True),
        sa.Column("marital_status", sa.String(255), nullable=True),
        sa.Column("wedding_day", sa.Date, nullable=True),
        sa.Column("citizenship", sa.String(255), nullable=True),
        sa.Column("permanent_address", sa.Text, nullable=True),
        sa.Column("blood_group", sa.String(255), nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("pan_card_number", sa.String(255), nullable=True),
        sa.Column("aadhaar_card_number", sa.String(255), nullable=True),
        sa.Column("passport_number", sa.String(255), nullable=True),
        sa.Column("uan_number", sa.String(255), nullable=True),
        sa.Column("emergency_contact_person_name", sa.String(255), nullable=True),
        sa.Column("emergency_contact_number", sa.String(255), nullable=True),
        sa.Column("emergency_contact_person_relation", sa.String(50), nullable=True),
        sa.Column("job_description", sa.Text, nullable=True),
        sa.Column("ask_me_about", sa.Text, nullable=True),
        sa.Column("about_me", sa.Text, nullable=True),
        sa.Column("can_update", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("tenth_school_name", sa.String(255), nullable=True),
        sa.Column("tenth_board", sa.String(255), nullable=True),
        sa.Column("tenth_field_of_study", sa.String(255), nullable=True),
        sa.Column("tenth_date_of_completion", sa.Date, nullable=True),
        sa.Column("twelfth_school_name", sa.String(255), nullable=True),
        sa.Column("twelfth_board", sa.String(255), nullable=True),
        sa.Column("twelfth_field_of_study", sa.String(255), nullable=True),
        sa.Column("twelfth_date_of_completion", sa.Date, nullable=True),
        sa.Column("graduation_school_name", sa.String(255), nullable=True),
        sa.Column("graduation_degree", sa.String(255), nullable=True),
        sa.Column("graduation_field_of_study", sa.String(255), nullable=True),
        sa.Column("graduation_date_of_completion", sa.Date, nullable=True),
        sa.Column("post_graduation_school_name", sa.String(255), nullable=True),
        sa.Column("post_graduation_degree", sa.String(255), nullable=True),
        sa.Column("post_graduation_field_of_study", sa.String(255), nullable=True),
        sa.Column("post_graduation_date_of_completion", sa.Date, nullable=True),
        sa.Column("passport_photo", sa.String(255), nullable=True),
        sa.Column("latest_cv", sa.String(255), nullable=True),
        sa.Column("aadhar_card", sa.String(255), nullable=True),
        sa.Column("pan_card", sa.String(255), nullable=True),
        sa.Column("marksheet_10th", sa.String(255), nullable=True),
        sa.Column("marksheet_12th", sa.String(255), nullable=True),
        sa.Column("sem_1", sa.Text, nullable=True),
        sa.Column("sem_2", sa.Text, nullable=True),
        sa.Column("sem_3", sa.Text, nullable=True),
        sa.Column("sem_4", sa.Text, nullable=True),
        sa.Column("sem_5", sa.Text, nullable=True),
        sa.Column("sem_6", sa.Text, nullable=True),
        sa.Column("sem_7", sa.Text, nullable=True),
        sa.Column("sem_8", sa.Text, nullable=True),
        sa.Column("pg_sem_1", sa.Text, nullable=True),
        sa.Column("pg_sem_2", sa.Text, nullable=True),
        sa.Column("pg_sem_3", sa.Text, nullable=True),
        sa.Column("pg_sem_4", sa.Text, nullable=True),
        sa.Column("consolidated_marksheet", sa.Text, nullable=True),
        sa.Column("pg_consolidated_marksheet", sa.Text, nullable=True),
        sa.Column("candidate_type", sa.Text, nullable=True),
        sa.Column("skill_set", sa.String(255), nullable=True),
        sa.Column("internship_start_date", sa.Date, nullable=True),
        sa.Column("internship_end_date", sa.Date, nullable=True),
        sa.Column("tentative_onboarding_date", sa.Date, nullable=True),
        sa.Column("mks_onboarding_date", sa.Date, nullable=True),
        sa.Column("training_mode", sa.String(255), nullable=True),
        sa.Column("training_plan", sa.String(255), nullable=True),
        sa.Column("training_start_date", sa.Date, nullable=True),
        sa.Column("training_end_date", sa.Date, nullable=True),
        sa.Column("evaluation_type", sa.String(255), nullable=True),
        sa.Column("evaluation_date", sa.Date, nullable=True),
        sa.Column("assessment_score", sa.String(255), nullable=True),
        sa.Column("trainer_notes", sa.String(255), nullable=True),
        sa.Column("allocation_date", sa.Date, nullable=True),
        sa.Column("account", sa.String(255), nullable=True),
        sa.Column("bu_head", sa.String(255), nullable=True),
        sa.Column("reporting_manager", sa.String(255), nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("job_title", sa.String(255), nullable=False),
        sa.Column("experience_from", sa.Integer, nullable=True),
        sa.Column("experience_to", sa.Integer, nullable=True),
        sa.Column("employment_type", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=False),
        sa.Column("edu_qualification", sa.String(255), nullable=False),
        sa.Column("key_skills", sa.Text, nullable=False),
        sa.Column("job_description", sa.Text, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("job_id", sa.BigInteger, sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("candidate_name", sa.String(255), nullable=False),
        sa.Column("candidate_number", sa.Integer, nullable=False),
        sa.Column("candidate_email", sa.String(255), nullable=False),
        sa.Column("candidate_address", sa.String(255), nullable=True),
        sa.Column("candidate_pin_code", sa.String(255), nullable=True),
        sa.Column("candidate_city", sa.String(255), nullable=True),
        sa.Column("candidate_state", sa.String(255), nullable=True),
        sa.Column("candidate_job_title", sa.String(255), nullable=True),
        sa.Column("candidate_experience_yrs", sa.Integer, nullable=True),
        sa.Column("candidate_experience_month", sa.Integer, nullable=True),
        sa.Column("candidate_employer", sa.String(255), nullable=True),
        sa.Column("candidate_location", sa.String(255), nullable=True),
        sa.Column("candidate_ctc", sa.String(255), nullable=True),
        sa.Column("candidate_expected_ctc", sa.String(255), nullable=True),
        sa.Column("candidate_doj", sa.Integer, nullable=False),
        sa.Column("candidate_resume", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("firstname", sa.String(255), nullable=False),
        sa.Column("lastname", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "clientsurvey",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("delivery", sa.Integer, nullable=False),
        sa.Column("quality", sa.Integer, nullable=False),
        sa.Column("expertise", sa.Integer, nullable=False),
        sa.Column("mksvalues", sa.Integer, nullable=False),
        sa.Column("overallservicesatisfaction", sa.Integer, nullable=False),
        sa.Column("comments", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "current_openings",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("job_title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("skills", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("account", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("status", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("email", sa.String(255), primary_key=True),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "profiles",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("father_name", sa.String(255), nullable=True),
        sa.Column("mother_name", sa.String(255), nullable=True),
        sa.Column("photo", sa.String(255), nullable=True),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("gender", sa.Text, nullable=True),
        sa.Column("mobile", sa.String(255), nullable=True),
        sa.Column("religion", sa.String(255), nullable=True),
        sa.Column("nationality", sa.String(255), nullable=True),
        sa.Column("aadhar", sa.String(255), nullable=True),
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("state", sa.String(255), nullable=True),
        sa.Column("district", sa.String(255), nullable=True),
        sa.Column("pincode", sa.String(255), nullable=True),
        sa.Column("perm_address_line1", sa.String(255), nullable=True),
        sa.Column("perm_address_line2", sa.String(255), nullable=True),
        sa.Column("perm_city", sa.String(255), nullable=True),
        sa.Column("perm_state", sa.String(255), nullable=True),
        sa.Column("perm_district", sa.String(255), nullable=True),
        sa.Column("perm_pincode", sa.String(255), nullable=True),
        sa.Column("tenth_board", sa.String(255), nullable=True),
        sa.Column("tenth_passing_year", sa.String(255), nullable=True),
        sa.Column("tenth_marksheet", sa.String(255), nullable=True),
        sa.Column("twelfth_board", sa.String(255), nullable=True),
        sa.Column("twelfth_passing_year", sa.String(255), nullable=True),
        sa.Column("twelfth_marksheet", sa.String(255), nullable=True),
        sa.Column("degree_name", sa.String(255), nullable=True),
        sa.Column("specialization", sa.String(255), nullable=True),
        sa.Column("university", sa.String(255), nullable=True),
        sa.Column("degree_passing_year", sa.String(255), nullable=True),
        sa.Column("degree_grade", sa.String(255), nullable=True),
        sa.Column("is_fresher", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("duration", sa.String(255), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("project_description", sa.Text, nullable=True),
        sa.Column("technologies", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("skill_id", sa.String(255), nullable=True, unique=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_category", sa.String(255), nullable=False),
        sa.Column("rating", sa.String(255), nullable=False),
        sa.Column("level_of_proficiency", sa.String(255), nullable=True),
        sa.Column("project_exposure", sa.Boolean, nullable=True),
        sa.Column("experience", sa.Boolean, nullable=True),
        sa.Column("active_in_the_project", sa.Boolean, nullable=True),
        sa.Column("attachment", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("mail_triggered", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("manager_rating", sa.String(255), nullable=True),
        sa.Column("skill_gap", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("account", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("no_skill_gap", sa.Boolean, nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "skill_configurations",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_category", sa.String(255), nullable=False),
        sa.Column("is_sub_skill_is_available", sa.Integer, nullable=True),
        sa.Column("status", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "sub_skills",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("skill_id", sa.String(255), sa.ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=True),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_category", sa.String(255), nullable=False),
        sa.Column("rating", sa.String(255), nullable=False),
        sa.Column("level_of_proficiency", sa.String(255), nullable=True),
        sa.Column("project_exposure", sa.Boolean, nullable=True),
        sa.Column("experience", sa.String(255), nullable=True),
        sa.Column("active_in_the_project", sa.Boolean, nullable=True),
        sa.Column("attachment", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("mail_triggered", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("manager_rating", sa.String(255), nullable=True),
        sa.Column("skill_gap", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("account", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("no_skill_gap", sa.Boolean, nullable=True),
    )

    op.create_table(
        "testimonials",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "update_requests",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(255), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("admin_note", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("update_requests")
    op.drop_table("testimonials")
    op.drop_table("sub_skills")
    op.drop_table("skill_configurations")
    op.drop_table("skills")
    op.drop_table("profiles")
    op.drop_table("password_reset_tokens")
    op.drop_table("current_openings")
    op.drop_table("clientsurvey")
    op.drop_table("clients")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("users")
