from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.hrms.db import HrmsBase


class SubSkillEntity(HrmsBase):
    __tablename__ = "sub_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    # References SkillEntity.skill_id (a UUID string), NOT SkillEntity.id - matches the
    # actual Eloquent relationship (hasMany(SubSkill, 'skill_id', 'skill_id')), which the
    # migration chain's "unsignedBigInteger -> skills.id" FK never actually matched in
    # practice (the live schema keeps this VARCHAR, confirming the bigint migration was
    # superseded/never effectively applied).
    skill_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("skills.skill_id", ondelete="CASCADE"))
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_category: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[str] = mapped_column(String(255), nullable=False)
    level_of_proficiency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_exposure: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    experience: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    skill: Mapped["SkillEntity"] = relationship(
        back_populates="sub_skills",
        primaryjoin="foreign(SubSkillEntity.skill_id) == SkillEntity.skill_id",
        lazy="selectin",
    )
