from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import BigIntPK, HrmsBase


class CertificateTemplateEntity(HrmsBase):
    """Every upload just inserts a new row - "the current global template" is simply
    the most recently uploaded one (ORDER BY created_at DESC LIMIT 1), so there's no
    separate singleton/settings table to manage."""

    __tablename__ = "certificate_templates"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingCertificateEntity(HrmsBase):
    __tablename__ = "training_certificates"
    __table_args__ = (UniqueConstraint("training_id", "trainee_id", name="uq_training_certificate_trainee"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    training_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("training_programs.id"), nullable=False)
    trainee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Snapshotted at issuance so the certificate stays accurate even if the training's
    # own topic is edited later.
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    issued_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
