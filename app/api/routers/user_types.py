from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user_type import UserTypeEntity
from app.schemas.user import UserTypeResponse

router = APIRouter(prefix="/api/users", tags=["user-types"], dependencies=[Depends(get_current_user)])


@router.get("/userTypes")
async def get_user_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserTypeEntity))
    types = [UserTypeResponse(id=e.id, name=e.type_name) for e in result.scalars().all()]
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=[t.model_dump() for t in types])
