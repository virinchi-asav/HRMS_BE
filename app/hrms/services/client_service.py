from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hrms.models.client import ClientEntity
from app.hrms.schemas.client import ClientUpsertRequest
from app.utils.pagination import PageResult, paginate


def _derive_username(email: str) -> str:
    """Mirrors ClientController::store/update: username = local-part of the email."""
    return email.split("@", 1)[0]


async def get_client(db: AsyncSession, client_id: int) -> ClientEntity | None:
    entity = await db.get(ClientEntity, client_id)
    if entity is None or entity.deleted_at is not None:
        return None
    return entity


async def list_clients(db: AsyncSession, page_number: int, page_size: int, search: str | None) -> PageResult:
    stmt = select(ClientEntity).where(ClientEntity.deleted_at.is_(None))
    if search:
        stmt = stmt.where(
            or_(ClientEntity.firstname.ilike(f"%{search}%"), ClientEntity.email.ilike(f"%{search}%"))
        )
    stmt = stmt.order_by(ClientEntity.id.desc())
    return await paginate(db, stmt, page_number, page_size)


async def create_client(db: AsyncSession, data: ClientUpsertRequest) -> ClientEntity:
    entity = ClientEntity(
        firstname=data.firstname,
        lastname=data.lastname,
        email=data.email,
        organization=data.organization,
        username=_derive_username(data.email),
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def update_client(db: AsyncSession, client_id: int, data: ClientUpsertRequest) -> ClientEntity | None:
    entity = await get_client(db, client_id)
    if entity is None:
        return None
    entity.firstname = data.firstname
    entity.lastname = data.lastname
    entity.email = data.email
    entity.organization = data.organization
    entity.username = _derive_username(data.email)
    await db.commit()
    await db.refresh(entity)
    return entity


async def delete_client(db: AsyncSession, client_id: int) -> bool:
    entity = await get_client(db, client_id)
    if entity is None:
        return False
    entity.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def restore_client(db: AsyncSession, client_id: int) -> bool:
    entity = await db.get(ClientEntity, client_id)
    if entity is None:
        return False
    entity.deleted_at = None
    await db.commit()
    return True
