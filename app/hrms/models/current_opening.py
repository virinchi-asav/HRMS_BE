from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import BigIntPK, HrmsBase

# MySQL (5.7.8+) has a native JSON column type, and plain sqlalchemy.JSON maps to it
# directly - matches the JSONB column in postgres_complete.sql closely enough (both
# store/retrieve the skills list transparently) and also works fine under SQLite in
# tests, so no dialect-specific variant is needed here.


class CurrentOpeningEntity(HrmsBase):
    __tablename__ = "current_openings"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Not present in the source schema - the Laravel route `restore/{id}` existed but
    # CurrentOpeningsController had no restore() and this model had no SoftDeletes, so
    # "restore" was dead on arrival. Added here to make that route actually work.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
