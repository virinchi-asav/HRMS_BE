from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.hrms.db import HrmsBase


class SkillEntity(HrmsBase):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    # UUID-string join key used by SubSkillEntity.skill_id (NOT this row's integer `id` -
    # SkillController generates this via Str::uuid() and SubSkill.skill() belongsTo
    # binds on this column). unique=True so sub_skills can carry a real FK to it.
    skill_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_category: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[str] = mapped_column(String(255), nullable=False)
    level_of_proficiency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_exposure: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Matches the live schema exactly: boolean here, but a free-text VARCHAR on
    # SubSkillEntity below - a genuine (if odd) asymmetry confirmed by postgres_complete.sql,
    # not something to "fix" since it reflects the real column type in production.
    experience: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    active_in_the_project: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    attachment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mail_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manager_rating: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skill_gap: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    no_skill_gap: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Not present in the source schema - see CurrentOpeningEntity's note: the
    # `restore/{skill_id}` route existed but was dead (no restore() method, no
    # SoftDeletes). Added here to make that route actually work.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sub_skills: Mapped[list["SubSkillEntity"]] = relationship(
        back_populates="skill",
        primaryjoin="foreign(SubSkillEntity.skill_id) == SkillEntity.skill_id",
        lazy="selectin",
    )
