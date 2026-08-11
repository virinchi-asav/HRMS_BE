from datetime import date, datetime

from pydantic import BaseModel


class MonthlyCount(BaseModel):
    month: str  # "YYYY-MM"
    count: int


class CategoryCount(BaseModel):
    account_id: int | None = None
    account_name: str  # resolved KMS account name, or "Unspecified"/"Not linked to a training"
    department_id: int | None = None
    department_name: str | None = None
    count: int


class ReportSection(BaseModel):
    total: int
    by_account: list[CategoryCount]
    by_month: list[MonthlyCount]


class TrainingReportResponse(BaseModel):
    range_start: date
    range_end: date
    months: int
    training_programs: ReportSection
    task_assessments: ReportSection


# ---- KMS usage (Document Library file-open activity) ----


class KmsAccountUsageCount(BaseModel):
    account_id: int | None = None
    account_name: str  # resolved KMS account name, or "Unspecified"
    user_count: int  # distinct users active in this account, within the window
    view_count: int  # total file-open events for this account, within the window


class KmsUserActivityRow(BaseModel):
    user_id: int
    user_name: str
    email: str
    account_id: int | None = None
    account_name: str  # "Unspecified" when the user has no kms_account_id set
    view_count: int
    last_viewed_at: datetime


class KmsUsageReportResponse(BaseModel):
    range_start: date
    range_end: date
    total_active_users: int  # distinct users with >=1 file-open in the window
    total_views: int
    by_account: list[KmsAccountUsageCount]
    # Sorted by view_count desc - directly answers "who are the frequent users".
    users: list[KmsUserActivityRow]
