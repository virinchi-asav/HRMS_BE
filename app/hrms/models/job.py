from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import BigIntPK, HrmsBase


class JobEntity(HrmsBase):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    edu_qualification: Mapped[str] = mapped_column(String(255), nullable=False)
    key_skills: Mapped[str] = mapped_column(Text, nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
