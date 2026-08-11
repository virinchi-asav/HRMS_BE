from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.core.config import hrms_settings
from app.hrms.core.deps import get_hrms_db
from app.hrms.schemas.webhook import WebhookDeleteUserRequest, WebhookUserSyncRequest
from app.hrms.services import user_service

router = APIRouter(prefix="/api/hrms/webhooks", tags=["hrms-webhooks"])


async def verify_webhook_api_key(x_api_key: str = Header(...)) -> None:
    """Closes the security gap in the source app: /api/hrms/webhooks/user-sync and
    /delete-user had NO authentication at all (any anonymous caller could create,
    update, or delete any user)."""
    if x_api_key != hrms_settings.hrms_webhook_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@router.post("/user-sync", dependencies=[Depends(verify_webhook_api_key)])
async def webhook_user_sync(payload: WebhookUserSyncRequest, db: AsyncSession = Depends(get_hrms_db)):
    try:
        user, is_new = await user_service.sync_user_from_webhook(db, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return {
        "status": "created" if is_new else "updated",
        "user_id": user.id,
        "message": f"User {'created' if is_new else 'updated'} successfully.",
    }


@router.delete("/delete-user", dependencies=[Depends(verify_webhook_api_key)])
async def webhook_delete_user(payload: WebhookDeleteUserRequest, db: AsyncSession = Depends(get_hrms_db)):
    ok = await user_service.delete_user_by_employee_id(db, payload.employee_id)
    return {"status": "deleted" if ok else "not_found"}
