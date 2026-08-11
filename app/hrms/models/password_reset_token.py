from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import HrmsBase


class PasswordResetTokenEntity(HrmsBase):
    """The legacy duplicate `password_resets` table (superseded, unwired in
    config/auth.php) is intentionally not modeled - this is the one Laravel actually
    uses."""

    __tablename__ = "password_reset_tokens"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
