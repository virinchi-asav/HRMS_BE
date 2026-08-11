"""Ports SkillController.php (the most complex controller in the source app).

Deliberate architecture change from the Laravel version: file attachments are uploaded
via a small dedicated endpoint (`upload_staged_attachment`) that returns a staged
filename, which the create/update JSON body then references - rather than trying to
replicate Laravel's single multipart-form-with-nested-array submission (which doesn't
map cleanly onto a JSON-first SPA API). All folder-naming conventions, validation
rules, mail-trigger conditions, and the manager-review-vs-owner-edit branching are
otherwise ported as exactly as the source PHP allows.

Deliberate bug fixes (per the "fix obvious bugs" decision):
- SkillController::update called saveSubSkills() twice in the owner-edit path, which
  would double-insert any brand-new sub-skill on every edit. Only called once here.
- Skill delete is now a real soft-delete (existing behavior hard-deleted the row AND
  immediately wiped the attachment folder, which is incompatible with the `restore`
  route that already existed in routes/web.php but had no backing implementation).
"""

import logging
import re
import uuid as uuid_lib
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.config import hrms_settings
from app.hrms.core.constants import Role
from app.hrms.models.skill import SkillEntity
from app.hrms.models.skill_configuration import SkillConfigurationEntity
from app.hrms.models.sub_skill import SubSkillEntity
from app.hrms.models.user import UserEntity
from app.hrms.schemas.skill import SkillReviewRequest, SkillUpsertRequest, SubSkillUpsertRequest
from app.hrms.services import email_service, file_storage_service, user_service
from app.hrms.utils.reporting import find_direct_reportees
from app.utils.pagination import PageResult, paginate

logger = logging.getLogger(__name__)

MANAGER_LIKE_ROLES = (Role.ADMIN, Role.MANAGER, Role.BU_HEAD)


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-")


async def get_user_names(db: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    result = await db.execute(select(UserEntity.id, UserEntity.name).where(UserEntity.id.in_(user_ids)))
    return {row.id: row.name for row in result.all()}


async def get_reporters(db: AsyncSession, user: UserEntity, selected_department: str | None) -> list[UserEntity]:
    """Mirrors SkillController::getReporters."""
    if user.role in (Role.ADMIN, Role.BU_HEAD):
        stmt = select(UserEntity).where(UserEntity.role != user.role)
    elif user.role == Role.MANAGER:
        stmt = select(UserEntity).where(UserEntity.reporting_to == str(user.id), UserEntity.role != Role.MANAGER)
    else:
        stmt = select(UserEntity).where(UserEntity.id == user.id)

    if selected_department:
        stmt = stmt.where(UserEntity.department == selected_department)

    result = await db.execute(stmt)
    seen: dict[int, UserEntity] = {}
    for u in result.scalars().all():
        seen[u.id] = u
    return list(seen.values())


async def list_skills(
    db: AsyncSession,
    current_user: UserEntity,
    page_number: int,
    page_size: int,
    department: str | None = None,
    skill_names: list[str] | None = None,
    active_in_the_project: int | None = None,
    skill_gap: str | None = None,
    reporter_ids: list[int] | None = None,
) -> dict:
    reporters = await get_reporters(db, current_user, department)

    stmt = select(SkillEntity).where(SkillEntity.deleted_at.is_(None))

    if skill_names:
        stmt = stmt.where(SkillEntity.skill_name.in_(skill_names))
    if department:
        stmt = stmt.where(
            exists().where(and_(UserEntity.id == SkillEntity.user_id, UserEntity.department == department))
        )
    if active_in_the_project is not None:
        sub_active_exists = exists().where(
            and_(SubSkillEntity.skill_id == SkillEntity.skill_id, SubSkillEntity.active_in_the_project.is_(True))
        )
        if active_in_the_project == 1:
            stmt = stmt.where(or_(SkillEntity.active_in_the_project.is_(True), sub_active_exists))
        else:
            stmt = stmt.where(SkillEntity.active_in_the_project.is_(False), ~sub_active_exists)

    if skill_gap == "1":
        stmt = stmt.where(or_(SkillEntity.no_skill_gap.is_(True), SkillEntity.skill_gap.is_not(None)))
    elif skill_gap == "0":
        stmt = stmt.where(
            or_(SkillEntity.no_skill_gap.is_(None), SkillEntity.no_skill_gap.is_(False)),
            SkillEntity.skill_gap.is_(None),
        )

    # applyReporterFilter
    requested_ids = set(reporter_ids or [])
    if current_user.role in (Role.ADMIN, Role.BU_HEAD):
        if requested_ids:
            stmt = stmt.where(SkillEntity.user_id.in_(requested_ids))
    elif current_user.role == Role.MANAGER:
        valid_ids = {r.id for r in reporters} | {current_user.id}
        filtered = requested_ids & valid_ids
        stmt = stmt.where(SkillEntity.user_id.in_(filtered if filtered else valid_ids))
    else:
        stmt = stmt.where(SkillEntity.user_id == current_user.id)

    skills_without_pagination = list((await db.execute(stmt)).scalars().unique().all())

    page_stmt = stmt.order_by(SkillEntity.id.desc())
    page_result = await paginate(db, page_stmt, page_number, page_size)

    departments = await _get_department_list(db)
    full_skills = await _get_full_skill_names(db, department)
    department_proficiencies = await _get_department_proficiencies(db, department)

    return {
        "page": page_result,
        "skills_without_pagination": skills_without_pagination,
        "departments": departments,
        "full_skills": full_skills,
        "department_proficiencies": department_proficiencies,
        "reporters": reporters,
    }


async def _get_department_list(db: AsyncSession) -> list[str]:
    result = await db.execute(select(UserEntity.department).where(UserEntity.department.is_not(None)).distinct())
    return sorted(set(result.scalars().all()))


async def _get_full_skill_names(db: AsyncSession, department: str | None) -> list[str]:
    stmt = select(SkillConfigurationEntity.skill_name)
    if department:
        stmt = stmt.where(SkillConfigurationEntity.department == department)
    result = await db.execute(stmt)
    return sorted(set(result.scalars().all()))


async def _get_department_proficiencies(db: AsyncSession, department: str | None) -> dict[str, float]:
    stmt = select(SkillEntity.level_of_proficiency, UserEntity.department).join(
        UserEntity, UserEntity.id == SkillEntity.user_id
    )
    if department:
        stmt = stmt.where(UserEntity.department == department)
    else:
        stmt = stmt.where(UserEntity.department.is_not(None))

    rows = (await db.execute(stmt)).all()
    buckets: dict[str, list[float]] = {}
    for proficiency, dept in rows:
        try:
            value = float(proficiency)
        except (TypeError, ValueError):
            continue
        buckets.setdefault(dept or "Unknown", []).append(value)

    return {dept: round(sum(values) / len(values), 2) for dept, values in buckets.items() if values}


async def get_skill_configs_for_department(db: AsyncSession, department: str | None) -> list[SkillConfigurationEntity]:
    stmt = select(SkillConfigurationEntity).where(
        SkillConfigurationEntity.status == 1, SkillConfigurationEntity.deleted_at.is_(None)
    )
    if department:
        stmt = stmt.where(SkillConfigurationEntity.department == department)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def export_skills_xlsx(
    db: AsyncSession,
    current_user: UserEntity,
    department: str | None = None,
    skill_names: list[str] | None = None,
    active_in_the_project: int | None = None,
    skill_gap: str | None = None,
    reporter_ids: list[int] | None = None,
) -> bytes:
    """Mirrors FilteredSkillsExport - reuses the exact same filter logic as list_skills."""
    import io

    import openpyxl

    result = await list_skills(
        db, current_user, 0, 1_000_000, department, skill_names, active_in_the_project, skill_gap, reporter_ids
    )
    skills = result["page"].items

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Skills Report"
    sheet.append(
        ["User Name", "Skill Name", "Skill Category", "Rating", "Proficiency (%)", "Skill Gap",
         "Project Exposure", "Experience (Years)", "Active in Project", "Start Date", "End Date",
         "Account", "Project Name", "Attachment", "Notes"]
    )
    for skill in skills:
        owner = await db.get(UserEntity, skill.user_id)
        sheet.append([
            owner.name if owner else "N/A",
            skill.skill_name,
            skill.skill_category,
            skill.rating,
            f"{skill.level_of_proficiency}%" if skill.level_of_proficiency else None,
            f"{skill.skill_gap}%" if skill.skill_gap else "—",
            "Yes" if skill.project_exposure else "No",
            skill.experience,
            "Yes" if skill.active_in_the_project else "No",
            skill.start_date.isoformat() if skill.start_date else None,
            skill.end_date.isoformat() if skill.end_date else None,
            skill.account,
            skill.project_name,
            skill.attachment or "No File",
            skill.notes,
        ])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def get_used_skill_names(db: AsyncSession, user_id: int) -> list[str]:
    own_skills = (await db.execute(select(SkillEntity.skill_name).where(SkillEntity.user_id == user_id))).scalars()
    own_skill_ids = select(SkillEntity.skill_id).where(SkillEntity.user_id == user_id)
    own_sub_skills = (
        await db.execute(select(SubSkillEntity.skill_name).where(SubSkillEntity.skill_id.in_(own_skill_ids)))
    ).scalars()
    return sorted(set(own_skills) | set(own_sub_skills))


async def get_skill_by_skill_id(db: AsyncSession, skill_id: str) -> SkillEntity | None:
    result = await db.execute(select(SkillEntity).where(SkillEntity.skill_id == skill_id))
    return result.scalar_one_or_none()


async def get_accounts(db: AsyncSession) -> list[str]:
    """The "account" dropdown on the skill add/edit form, matching createEditSkillForm's
    $accounts - delegates to user_service so this stays in sync with the same dropdown
    on the User Profile's Project Allocation section."""
    return await user_service.get_accounts(db)


def _staging_dir(user_id: int) -> Path:
    return Path(hrms_settings.hrms_upload_root) / "users" / str(user_id) / "skill" / "_staged"


async def upload_staged_attachment(user_id: int, file: UploadFile) -> str:
    """Saves an uploaded attachment to a per-user staging area and returns the stored
    filename for the client to reference in a subsequent create/update call."""
    content = await file.read()
    stored_name = file_storage_service.unique_filename(file.filename)
    await file_storage_service.save_file(_staging_dir(user_id), stored_name, content)
    return stored_name


def _move_attachment_into_place(
    user_id: int, staged_filename: str | None, skill_slug: str, sub_skill_slug: str | None, previous: str | None
) -> str | None:
    """Moves a staged attachment (or keeps/deletes the existing one) - synchronous
    filesystem helper used by create/update below."""
    if not staged_filename:
        return previous

    target_dir = file_storage_service.skill_attachment_dir(user_id, skill_slug, sub_skill_slug)
    target_dir.mkdir(parents=True, exist_ok=True)

    staged_path = _staging_dir(user_id) / staged_filename
    if previous:
        file_storage_service.delete_file(target_dir / previous)
    if staged_path.exists():
        staged_path.rename(target_dir / staged_filename)
    return staged_filename


async def create_skill(db: AsyncSession, current_user: UserEntity, data: SkillUpsertRequest) -> SkillEntity:
    skill_slug = slugify(data.skill_name)
    attachment_name = None if data.remove_attachment else data.attachment

    entity = SkillEntity(
        skill_id=str(uuid_lib.uuid4()),
        user_id=current_user.id,
        skill_name=data.skill_name,
        skill_category=data.skill_category,
        rating=data.rating,
        level_of_proficiency=data.level_of_proficiency,
        project_exposure=bool(data.project_exposure),
        experience=bool(data.experience),
        active_in_the_project=bool(data.active_in_the_project),
        attachment=_move_attachment_into_place(current_user.id, attachment_name, skill_slug, None, None),
        start_date=data.start_date,
        end_date=data.end_date,
        account=data.account,
        project_name=data.project_name,
        notes=data.notes,
        no_skill_gap=bool(data.no_skill_gap),
    )
    db.add(entity)
    await db.flush()

    active_sub_skill_exists = await _save_sub_skills(db, entity, data.sub_skills, current_user.id, skill_slug)

    if entity.active_in_the_project or active_sub_skill_exists:
        await _notify_manager_skill_activated(db, current_user, entity)

    await db.commit()
    await db.refresh(entity)
    return entity


# Mirrors the 1-5 scale used by the Skills form's Rating dropdown (SkillForm.jsx's
# RATING_OPTIONS) - kept here since this is the one place the backend needs to compute
# a proficiency % itself, for the Task Assessment auto-log flow below.
RATING_TO_PROFICIENCY = {"1": 0, "2": 25, "3": 50, "4": 75, "5": 100}


async def auto_log_skill_from_task_pass(
    db: AsyncSession, trainee_id: int, skill_name: str, skill_category: str | None, rating: str
) -> None:
    """Called when a trainee passes a Task Assessment that has a Skill configured (see
    TaskEntity.skill_name) - logs it on their Skills module profile, or upgrades an
    existing entry's rating, but never downgrades one the trainee already rated higher
    themselves. New entries default Account to "Theoretical/Online-Course" and No Skill
    Gap to true, per the Task Assessment feature spec - this is a passive, automated
    log, not a claim of hands-on project experience."""
    result = await db.execute(
        select(SkillEntity).where(
            SkillEntity.user_id == trainee_id,
            SkillEntity.deleted_at.is_(None),
            func.lower(SkillEntity.skill_name) == skill_name.strip().lower(),
        )
    )
    existing = result.scalars().first()
    new_proficiency = RATING_TO_PROFICIENCY.get(rating, 0)

    if existing is not None:
        try:
            existing_rating_value = int(existing.rating)
        except (TypeError, ValueError):
            existing_rating_value = 0
        if int(rating) <= existing_rating_value:
            return
        existing.rating = rating
        existing.level_of_proficiency = str(new_proficiency)
        await db.commit()
        return

    entity = SkillEntity(
        skill_id=str(uuid_lib.uuid4()),
        user_id=trainee_id,
        skill_name=skill_name,
        skill_category=skill_category or "",
        rating=rating,
        level_of_proficiency=str(new_proficiency),
        account="Theoretical/Online-Course",
        no_skill_gap=True,
    )
    db.add(entity)
    await db.commit()


async def _save_sub_skills(
    db: AsyncSession,
    skill: SkillEntity,
    submitted: list[SubSkillUpsertRequest],
    user_id: int,
    skill_slug: str,
) -> bool:
    existing = (
        (await db.execute(select(SubSkillEntity).where(SubSkillEntity.skill_id == skill.skill_id))).scalars().all()
    )
    existing_by_id = {s.id: s for s in existing}
    submitted_ids: set[int] = set()
    active_found = False

    for item in submitted:
        if item.id and item.id in existing_by_id:
            sub = existing_by_id[item.id]
        else:
            sub = SubSkillEntity(skill_id=skill.skill_id)
            db.add(sub)

        sub_slug = slugify(item.sub_skill_name)
        staged_attachment = item.attachment
        if item.remove_attachment:
            if sub.attachment:
                file_storage_service.delete_file(
                    file_storage_service.skill_attachment_dir(user_id, skill_slug, sub_slug) / sub.attachment
                )
            sub.attachment = None
        elif staged_attachment:
            sub.attachment = _move_attachment_into_place(
                user_id, staged_attachment, skill_slug, sub_slug, sub.attachment
            )

        sub.skill_name = item.sub_skill_name
        sub.skill_category = item.sub_skill_category
        sub.rating = item.rating
        sub.level_of_proficiency = item.level_of_proficiency
        sub.project_exposure = bool(item.project_exposure)
        sub.experience = item.experience
        sub.active_in_the_project = bool(item.active_in_the_project)
        sub.start_date = item.start_date
        sub.end_date = item.end_date
        sub.account = item.account
        sub.project_name = item.project_name
        sub.notes = item.notes
        sub.no_skill_gap = bool(item.no_skill_gap)

        if sub.active_in_the_project:
            sub.mail_triggered = True
            active_found = True

        await db.flush()
        submitted_ids.add(sub.id)

    to_delete = [s for s in existing if s.id not in submitted_ids]
    for sub in to_delete:
        sub_slug = slugify(sub.skill_name)
        if sub.attachment:
            file_storage_service.delete_file(
                file_storage_service.skill_attachment_dir(user_id, skill_slug, sub_slug) / sub.attachment
            )
        await db.delete(sub)

    return active_found


async def _notify_manager_skill_activated(db: AsyncSession, user: UserEntity, skill: SkillEntity) -> None:
    if not user.reporting_to:
        return
    try:
        manager_id = int(user.reporting_to)
    except ValueError:
        return
    manager = await db.get(UserEntity, manager_id)
    if not manager or not manager.email:
        return

    skills_url = f"{hrms_settings.hrms_frontend_base_url}/skills/edit/{skill.skill_id}"
    html = (
        f"<p>{user.name} has an active-in-project skill update requiring your review.</p>"
        f"<p><b>Skill:</b> {skill.skill_name} (Category: {skill.skill_category})</p>"
        f"<p><a href='{skills_url}'>Review skill</a></p>"
    )
    sent = await email_service.send_email(manager.email, "Skill Activated - Review Needed", html)
    if sent:
        skill.mail_triggered = True


async def is_reviewing_reportees_skill(db: AsyncSession, current_user: UserEntity, skill: SkillEntity) -> bool:
    """Determines which of the two update branches applies - mirrors SkillController::
    update's condition: `($user->role in [1,5,7]) && $reporterIds->contains($skill->user_id)`."""
    if current_user.role not in MANAGER_LIKE_ROLES:
        return False
    reportees = await find_direct_reportees(db, current_user.id)
    return skill.user_id in {r.id for r in reportees}


async def update_skill_as_reviewer(
    db: AsyncSession, current_user: UserEntity, skill: SkillEntity, data: SkillReviewRequest
) -> str:
    """Manager reviewing a direct reportee's skill (SkillController::update, branch A) -
    limited field set, drives skill-gap computation/notification."""
    original_rating = skill.level_of_proficiency
    skill.start_date = data.start_date
    skill.end_date = data.end_date
    skill.account = data.account
    skill.notes = data.notes
    skill.project_name = data.project_name
    skill.no_skill_gap = bool(data.no_skill_gap)

    if skill.mail_triggered and data.sub_skills:
        # level_of_proficiency for the parent skill isn't part of SkillReviewRequest's
        # narrow field set in the source form; sub-skill ratings are handled below.
        pass

    await db.flush()

    if data.sub_skills:
        for item in data.sub_skills:
            if not item.id:
                continue
            sub = await db.get(SubSkillEntity, item.id)
            if sub is None:
                continue
            sub.start_date = item.start_date
            sub.end_date = item.end_date
            sub.account = item.account
            sub.project_name = item.project_name
            sub.notes = item.notes
            sub.no_skill_gap = bool(item.no_skill_gap)
            if sub.mail_triggered and item.level_of_proficiency and sub.level_of_proficiency != item.level_of_proficiency:
                _apply_skill_gap(sub, item.level_of_proficiency)
                sub.rating = item.rating

    await db.commit()
    return "Ratings updated successfully."


def _apply_skill_gap(entity, new_proficiency: str) -> None:
    try:
        original = int(entity.level_of_proficiency)
        new = int(new_proficiency)
    except (TypeError, ValueError):
        entity.level_of_proficiency = new_proficiency
        return
    diff = abs(original - new)
    entity.skill_gap = f"{'+' if new > original else '-'} {diff}"
    entity.level_of_proficiency = new_proficiency


async def update_skill_as_owner(
    db: AsyncSession, current_user: UserEntity, skill: SkillEntity, data: SkillUpsertRequest
) -> SkillEntity:
    """Owner (or an Admin editing a skill that isn't one of their own direct reportees')
    full-edit path (SkillController::update, branch B)."""
    original_rating = skill.level_of_proficiency
    skill_slug = slugify(skill.skill_name)
    new_slug = slugify(data.skill_name)

    if skill_slug != new_slug:
        old_dir = file_storage_service.skill_attachment_dir(skill.user_id, skill_slug)
        new_dir = file_storage_service.skill_attachment_dir(skill.user_id, new_slug)
        if old_dir.exists():
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            old_dir.rename(new_dir)

    if data.remove_attachment and skill.attachment:
        file_storage_service.delete_file(
            file_storage_service.skill_attachment_dir(skill.user_id, new_slug) / skill.attachment
        )
        skill.attachment = None
    else:
        skill.attachment = _move_attachment_into_place(
            skill.user_id, data.attachment, new_slug, None, skill.attachment
        )

    skill.skill_name = data.skill_name
    skill.skill_category = data.skill_category
    skill.rating = data.rating
    skill.level_of_proficiency = data.level_of_proficiency
    skill.project_exposure = bool(data.project_exposure)
    skill.experience = bool(data.experience)
    skill.active_in_the_project = bool(data.active_in_the_project)
    skill.start_date = data.start_date
    skill.end_date = data.end_date
    skill.account = data.account
    skill.project_name = data.project_name
    skill.notes = data.notes
    skill.no_skill_gap = bool(data.no_skill_gap)

    active_sub_skill_exists = await _save_sub_skills(db, skill, data.sub_skills, skill.user_id, new_slug)

    if (
        (skill.active_in_the_project or active_sub_skill_exists)
        and original_rating != data.level_of_proficiency
    ):
        owner = await db.get(UserEntity, skill.user_id)
        if owner:
            await _notify_manager_skill_activated(db, owner, skill)

    await db.commit()
    await db.refresh(skill)
    return skill


async def delete_skill(db: AsyncSession, skill_id: str) -> bool:
    """Soft-delete (see module docstring for why this differs from the source app's
    immediate hard-delete + folder wipe)."""
    skill = await get_skill_by_skill_id(db, skill_id)
    if skill is None:
        return False
    skill.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def restore_skill(db: AsyncSession, skill_id: str) -> bool:
    skill = await get_skill_by_skill_id(db, skill_id)
    if skill is None:
        return False
    skill.deleted_at = None
    await db.commit()
    return True
