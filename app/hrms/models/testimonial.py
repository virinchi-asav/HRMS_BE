from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import HrmsBase


class TestimonialEntity(HrmsBase):
    """Matches the live schema exactly: no content columns exist beyond id/timestamps.
    TestimonialController::index just renders an empty list view - this looks like an
    unfinished feature rather than a bug to fix; flagging for a product decision on what
    fields (author, quote, rating?) should actually be added, rather than guessing."""

    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
