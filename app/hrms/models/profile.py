from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import HrmsBase


class ProfileEntity(HrmsBase):
    """Maps to the `profiles` table. NOTE: this table is orphaned in the source Laravel
    app - no Eloquent model or controller references it (its fields were superseded by
    equivalent columns added directly to `users`). Modeled here for schema completeness
    only; no service/router is built on top of it since there's no real business logic
    to port. Confirm with the business whether this table is truly dead before dropping
    it, or whether some external system still writes to it."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    father_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mother_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dob: Mapped[date | None] = mapped_column(nullable=True)
    gender: Mapped[str | None] = mapped_column(Text, nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(255), nullable=True)
    religion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aadhar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_pincode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenth_board: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenth_passing_year: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenth_marksheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twelfth_board: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twelfth_passing_year: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twelfth_marksheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree_passing_year: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree_grade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_fresher: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
