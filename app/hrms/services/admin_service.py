"""Ports AdminController.php - the profile review / update-request approval workflow."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.constants import Role
from app.hrms.models.update_request import UpdateRequestEntity
from app.hrms.models.user import UserEntity
from app.hrms.services.email_service import send_email


async def list_pending_update_requests(db: AsyncSession) -> list[UpdateRequestEntity]:
    result = await db.execute(select(UpdateRequestEntity).where(UpdateRequestEntity.status == "pending"))
    return list(result.scalars().unique().all())


async def list_all_update_requests(db: AsyncSession) -> list[UpdateRequestEntity]:
    result = await db.execute(select(UpdateRequestEntity).order_by(UpdateRequestEntity.created_at.desc()))
    return list(result.scalars().unique().all())


async def create_update_request(db: AsyncSession, user: UserEntity, reason: str | None) -> UpdateRequestEntity | None:
    """Mirrors CandidateController::requestUpdate - refuses if the user is already
    allowed to update their profile."""
    if user.can_update:
        return None
    entity = UpdateRequestEntity(user_id=user.id, reason=reason, status="pending")
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def handle_update_request(
    db: AsyncSession, request_id: int, action: str, admin_note: str | None
) -> UpdateRequestEntity | None:
    entity = await db.get(UpdateRequestEntity, request_id)
    if entity is None:
        return None

    user = await db.get(UserEntity, entity.user_id)

    if action == "approve":
        if user:
            user.can_update = True
        entity.status = "approved"
    elif action == "reject":
        entity.status = "rejected"
    else:
        raise ValueError("Invalid action.")

    entity.admin_note = admin_note
    await db.commit()
    await db.refresh(entity)

    if user and user.email:
        html = (
            f"<p>Your profile update request has been <b>{entity.status}</b>.</p>"
            + (f"<p>Note: {admin_note}</p>" if admin_note else "")
        )
        await send_email(user.email, "Update Request Status", html)

    return entity


async def get_pending_profiles(db: AsyncSession) -> list[UserEntity]:
    result = await db.execute(select(UserEntity).where(UserEntity.status.in_(["pending", "needs_update"])))
    return list(result.scalars().all())


async def get_profile_for_review(db: AsyncSession, user_id: int) -> UserEntity | None:
    return await db.get(UserEntity, user_id)


async def submit_profile_review(
    db: AsyncSession, user_id: int, reviewer_id: int, admin_message: str | None, status: str
) -> UserEntity | None:
    user = await db.get(UserEntity, user_id)
    if user is None:
        return None

    user.admin_message = admin_message
    user.status = status
    user.can_update = status == "needs_update"
    user.reviewed_by = reviewer_id
    user.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    if user.email:
        if status == "reviewed_accepted":
            html = "<p>Your profile has been reviewed and accepted.</p>"
            subject = "Profile Accepted"
        else:
            html = f"<p>Your profile needs updates.</p>" + (f"<p>{admin_message}</p>" if admin_message else "")
            subject = "Profile Needs Update"
        await send_email(user.email, subject, html)

    return user


async def export_candidates_name_email_xlsx(db: AsyncSession) -> bytes:
    """Mirrors AdminController::exportCandidates / CandidateExport - name+email only,
    role=4 (Candidate)."""
    import io

    import openpyxl

    result = await db.execute(select(UserEntity.name, UserEntity.email).where(UserEntity.role == Role.CANDIDATE))
    rows = result.all()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["name", "email"])
    for name, email in rows:
        sheet.append([name, email])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
