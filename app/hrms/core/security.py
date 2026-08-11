from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.hrms.core.config import hrms_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_ALGORITHM = "HS512"


def hash_password(plain_password: str) -> str:
    """Bcrypt, same as Laravel's Hash::make() default driver - existing Laravel-hashed
    passwords (if any user data is migrated across) remain verifiable."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, user_id: int, email: str, role: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=hrms_settings.hrms_jwt_expiration_minutes),
    }
    return jwt.encode(payload, hrms_settings.hrms_jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, hrms_settings.hrms_jwt_secret, algorithms=[JWT_ALGORITHM])
