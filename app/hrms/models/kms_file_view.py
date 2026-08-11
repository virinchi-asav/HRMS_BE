from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import BigIntPK, HrmsBase


class KmsFileViewEntity(HrmsBase):
    """One row per (user, file-open) event in the KMS Document Library - written by
    app.services.content_service.record_file_view when a user opens a file from
    DocumentLibrary.jsx. Lives in the HRMS database (like every other new feature
    table) even though file_id logically references the KMS module's own database
    (mks_lms_content.fileId, a separate MySQL DB/declarative Base) - that's a plain int,
    resolved against the KMS ContentEntity in the service layer, same cross-database
    convention as TrainingProgramEntity.account_id."""

    __tablename__ = "kms_file_views"
    __table_args__ = (Index("ix_kms_file_views_viewed_at", "viewed_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    file_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
