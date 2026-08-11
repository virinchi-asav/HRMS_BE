from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.pagination import PageResult, paginate


async def crud_get_by_id(db: AsyncSession, model: type, pk_col, pk_value: int) -> Any | None:
    result = await db.execute(select(model).where(pk_col == pk_value))
    return result.scalar_one_or_none()


async def crud_get_by_name(db: AsyncSession, model: type, name_col, name_value: str) -> Any | None:
    result = await db.execute(select(model).where(name_col == name_value))
    return result.scalar_one_or_none()


async def crud_delete(db: AsyncSession, model: type, pk_col, pk_value: int) -> None:
    entity = await crud_get_by_id(db, model, pk_col, pk_value)
    if entity is not None:
        await db.delete(entity)
        await db.commit()


async def crud_paginate(
    db: AsyncSession,
    model: type,
    pk_col,
    page_number: int,
    page_size: int,
    exclude_sentinel_col=None,
) -> PageResult:
    stmt = select(model)
    if exclude_sentinel_col is not None:
        stmt = stmt.where(exclude_sentinel_col != 0)
    stmt = stmt.order_by(pk_col.asc())
    return await paginate(db, stmt, page_number, page_size)
