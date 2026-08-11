from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.hrms.db import BigIntPK, HrmsBase


class CandidateEntity(HrmsBase):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id"), nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_number: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_pin_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_experience_yrs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_experience_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_employer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_ctc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_expected_ctc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_doj: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_resume: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    job: Mapped["JobEntity"] = relationship(lazy="selectin")
