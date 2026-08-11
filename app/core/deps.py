import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_IDS
from app.core.exceptions import AuthEntryPointException
from app.db.session import get_db
from app.hrms.core.constants import HRMS_TO_KMS_ROLE, Role
from app.hrms.core.security import decode_access_token as decode_hrms_access_token
from app.hrms.db import get_hrms_db
from app.hrms.models.user import UserEntity as HrmsUserEntity

__all__ = ["get_db", "LoggedInUser", "get_current_user"]

_bearer_scheme = HTTPBearer(auto_error=False)


class LoggedInUser(BaseModel):
    """The authenticated principal for the current request.

    KMS authenticates via the single HRMS login/JWT (no more separate KMS signin) -
    `role`/`role_id` are the KMS role the user's HRMS role maps to (see
    HRMS_TO_KMS_ROLE), not a "login as" choice anymore. `department_id`/`account_id`/
    `user_type_id` come from the 3 KMS-scoping columns added directly to the HRMS
    `users` table (kms_department_id/kms_account_id/kms_user_type_id).
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: str
    email: str
    role: str
    role_id: int
    department_id: int | None = None
    account_id: int | None = None
    user_type_id: int | None = None
    enabled: bool
    password_reset_required: bool | None = None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    hrms_db: AsyncSession = Depends(get_hrms_db),
) -> LoggedInUser:
    """Decodes the HRMS bearer token, loads the HRMS user via the HRMS engine (kept
    separate from the KMS `get_db` session on purpose - production points both at the
    same physical HRMS_DEV database, but nothing here should rely on that coincidence),
    and maps their HRMS role to a KMS role via HRMS_TO_KMS_ROLE."""
    if credentials is None:
        raise AuthEntryPointException(request.url.path)

    try:
        payload = decode_hrms_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AuthEntryPointException(request.url.path, "Invalid or expired token")

    user = await hrms_db.get(HrmsUserEntity, user_id)
    if user is None or user.deleted_at is not None:
        raise AuthEntryPointException(request.url.path, "User not found")

    try:
        hrms_role = Role(user.role)
    except ValueError:
        hrms_role = None
    role_enum = HRMS_TO_KMS_ROLE.get(hrms_role) if hrms_role is not None else None
    if role_enum is None:
        raise AuthEntryPointException(request.url.path, "This role is not permitted to access KMS")

    return LoggedInUser(
        user_id=user.id,
        user_name=user.name,
        email=user.email,
        role=role_enum.value,
        role_id=ROLE_IDS[role_enum],
        department_id=user.kms_department_id,
        account_id=user.kms_account_id,
        user_type_id=user.kms_user_type_id,
        enabled=user.deleted_at is None,
        password_reset_required=False,
    )
