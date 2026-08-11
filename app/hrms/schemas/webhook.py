from datetime import date

from pydantic import BaseModel, EmailStr


class WebhookUserSyncRequest(BaseModel):
    """Mirrors UserController::webhookUserSync's validated field set. `role` is a
    textual role name (e.g. "Admin", "Team Lead", "Manager", "BU Head") mapped to the
    numeric Role by the service, matching the original saveUserData() logic."""

    email: EmailStr
    name: str
    role: str
    password: str | None = None
    employee_id: str
    reporting_to: str | None = None
    gender: str | None = None
    marital_status: str | None = None
    birth_date: date | None = None
    wedding_day: date | None = None
    father_name: str | None = None
    emergency_contact_person_name: str | None = None
    emergency_contact_number: str | None = None
    work_location: str | None = None
    project_name: str | None = None
    source_of_hire: str | None = None
    job_title: str | None = None
    department: str | None = None
    total_experience: str | None = None
    experience: str | None = None
    date_of_joining: date | None = None
    employee_type: str | None = None
    employee_status: str | None = None
    job_description: str | None = None
    ask_me_about: str | None = None
    about_me: str | None = None


class WebhookDeleteUserRequest(BaseModel):
    employee_id: str
