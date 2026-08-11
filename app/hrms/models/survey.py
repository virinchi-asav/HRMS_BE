from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.hrms.db import BigIntPK, HrmsBase


class SurveyEntity(HrmsBase):
    """Maps to the `clientsurvey` table (Laravel's Survey model overrides $table -
    default would have been `surveys`)."""

    __tablename__ = "clientsurvey"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clients.id"), nullable=False)
    delivery: Mapped[int] = mapped_column(Integer, nullable=False)
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    expertise: Mapped[int] = mapped_column(Integer, nullable=False)
    mksvalues: Mapped[int] = mapped_column(Integer, nullable=False)
    overallservicesatisfaction: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped["ClientEntity"] = relationship(lazy="selectin")
