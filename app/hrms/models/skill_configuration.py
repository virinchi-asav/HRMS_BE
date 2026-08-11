from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.hrms.db import HrmsBase


class SkillConfigurationEntity(HrmsBase):
    __tablename__ = "skill_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_category: Mapped[str] = mapped_column(String(255), nullable=False)
    is_sub_skill_is_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Not present in the source schema - same dead-restore-route fix as Skill/CurrentOpening.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
