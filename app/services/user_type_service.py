from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_type import UserTypeEntity
from app.services import generic_crud


async def find_by_user_type_id(db: AsyncSession, user_type_id: int) -> UserTypeEntity | None:
    return await generic_crud.crud_get_by_id(db, UserTypeEntity, UserTypeEntity.id, user_type_id)


async def find_by_type_name(db: AsyncSession, type_name: str) -> UserTypeEntity | None:
    return await generic_crud.crud_get_by_name(db, UserTypeEntity, UserTypeEntity.type_name, type_name)
