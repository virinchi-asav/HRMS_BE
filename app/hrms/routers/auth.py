import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.config import hrms_settings
from app.hrms.core.deps import CurrentHrmsUser, get_current_hrms_user, get_hrms_db
from app.hrms.core.security import create_access_token, hash_password, verify_password
from app.hrms.models.password_reset_token import PasswordResetTokenEntity
from app.hrms.models.user import UserEntity
from app.hrms.schemas.auth import ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenResponse
from app.hrms.schemas.user import UserResponse
from app.hrms.services import user_service
from app.hrms.services.email_service import send_email

router = APIRouter(prefix="/api/hrms/auth", tags=["hrms-auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_hrms_db)):
    user = await user_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user), db: AsyncSession = Depends(get_hrms_db)
):
    user = await user_service.get_user(db, current_user.id)
    return UserResponse.model_validate(user)


@router.patch("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentHrmsUser = Depends(get_current_hrms_user),
    db: AsyncSession = Depends(get_hrms_db),
):
    """Mirrors LoginController::storechangePassword."""
    if payload.password != payload.password_confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    user = await user_service.get_user(db, current_user.id)
    if not verify_password(payload.current_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password = hash_password(payload.password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_hrms_db)):
    user = await user_service.get_by_email(db, payload.email)
    if user is None:
        # Same response regardless of whether the email exists, to avoid account enumeration.
        return {"message": "If that email exists, a reset link has been sent."}

    token = str(uuid.uuid4())
    existing = await db.get(PasswordResetTokenEntity, payload.email)
    if existing:
        existing.token = token
        existing.created_at = datetime.utcnow()
    else:
        db.add(PasswordResetTokenEntity(email=payload.email, token=token, created_at=datetime.utcnow()))
    await db.commit()

    reset_link = f"{hrms_settings.hrms_frontend_base_url}/reset-password?email={payload.email}&token={token}"
    html = f"<p>Reset your MKS HRMS password:</p><p><a href='{reset_link}'>{reset_link}</a></p>"
    await send_email(payload.email, "Reset Your Password", html)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_hrms_db)):
    result = await db.execute(select(PasswordResetTokenEntity).where(PasswordResetTokenEntity.email == payload.email))
    record = result.scalar_one_or_none()
    if record is None or record.token != payload.token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    expiry = (record.created_at or datetime.utcnow()) + timedelta(minutes=hrms_settings.hrms_password_reset_expiry_minutes)
    if datetime.utcnow() > expiry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = await user_service.get_by_email(db, payload.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password = hash_password(payload.password)
    await db.delete(record)
    await db.commit()
    return {"message": "Password reset successfully"}
