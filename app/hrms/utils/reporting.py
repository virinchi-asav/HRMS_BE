import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.user import UserEntity

EMPLOYEE_ID_PATTERN = re.compile(r"MKS/\d+(?:/\d{2}-\d{2})?")

# Employee IDs hard-coded as BU Head in the source app "because there is no option for
# BU Head on the Zoho side" - ported verbatim from UserController::saveUserData.
FORCED_BU_HEAD_EMPLOYEE_IDS = {
    "MKS/00003",
    "MKS/00002",
    "MKS/00053",
    "MKS/00222/22-23",
    "MKS/00271/22-23",
}


def extract_employee_id(raw_reporting_to: str | None) -> str | None:
    """Pulls an "MKS/00003"-style employee id out of a free-text string (as sent by an
    external HR system). Only used during webhook ingestion - see note on
    UserEntity.reporting_to: once normalized, that column holds the manager's plain
    user id (as a string), not this formatted code."""
    if not raw_reporting_to:
        return None
    match = EMPLOYEE_ID_PATTERN.search(raw_reporting_to)
    return match.group(0) if match else None


async def find_direct_reportees(db: AsyncSession, manager_id: int, exclude_self: bool = True) -> list[UserEntity]:
    """Mirrors `User::where('reporting_to', $user->id)` - reporting_to stores the
    manager's raw id as a string once normalized."""
    stmt = select(UserEntity).where(UserEntity.reporting_to == str(manager_id))
    if exclude_self:
        stmt = stmt.where(UserEntity.id != manager_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
