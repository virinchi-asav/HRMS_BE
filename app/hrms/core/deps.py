from collections.abc import Iterable

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthEntryPointException
from app.hrms.core.constants import Role
from app.hrms.core.security import decode_access_token
from app.hrms.db import get_hrms_db
from app.hrms.models.user import UserEntity

__all__ = ["get_hrms_db", "CurrentHrmsUser", "get_current_hrms_user", "require_role"]

_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentHrmsUser(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    name: str
    role: int


async def get_current_hrms_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_hrms_db),
) -> CurrentHrmsUser:
    if credentials is None:
        raise AuthEntryPointException(request.url.path)

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AuthEntryPointException(request.url.path, "Invalid or expired token")

    user = await db.get(UserEntity, user_id)
    if user is None or user.deleted_at is not None:
        raise AuthEntryPointException(request.url.path, "User not found")

    return CurrentHrmsUser(id=user.id, email=user.email, name=user.name, role=user.role)


def require_role(*roles: Role | int):
    """Mirrors Laravel's `role:1,5,7` middleware - a dependency factory that gates a
    route to specific roles."""
    allowed = {int(r) for r in roles}

    async def _check(user: CurrentHrmsUser = Depends(get_current_hrms_user)) -> CurrentHrmsUser:
        if user.role not in allowed:
            from app.core.exceptions import UserUnauthorizedException

            raise UserUnauthorizedException("User not authorized for this role")
        return user

    return _check
