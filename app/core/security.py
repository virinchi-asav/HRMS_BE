from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_ALGORITHM = "HS512"


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, subject_email: str, login_as_role: str) -> str:
    """Mirrors JwtUtils.generateJwtToken: sub=email, aud=loginAs role, HS512."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject_email,
        "aud": login_as_role,
        "iat": now,
        "exp": now + timedelta(milliseconds=settings.jwt_expiration_ms),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError on invalid/expired token.

    verify_aud is disabled because the audience claim is a dynamic role string
    chosen at login time, not a fixed expected audience.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"verify_aud": False},
    )
