import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceException
from app.models.category import CategoryEntity
from app.schemas.category import CategoryRequestModel
from app.services import generic_crud
from app.utils.excel_import import read_excel_rows
from app.utils.pagination import PageResult

logger = logging.getLogger(__name__)


async def add_category(db: AsyncSession, data: CategoryRequestModel) -> None:
    try:
        entity = CategoryEntity(
            category_name=data.category_name,
            category_description=data.category_description,
            unrestricted_category=data.unrestricted_category,
        )
        db.add(entity)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the add category name %s", data.category_name)
        raise ServiceException(str(e)) from e


async def edit_category(db: AsyncSession, category_id: int, data: CategoryRequestModel) -> None:
    try:
        entity = await generic_crud.crud_get_by_id(db, CategoryEntity, CategoryEntity.category_id, category_id)
        if entity is not None:
            entity.category_name = data.category_name
            entity.category_description = data.category_description
            entity.unrestricted_category = data.unrestricted_category
            await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the edit category name %s", data.category_name)
        raise ServiceException(str(e)) from e


async def delete_category(db: AsyncSession, category_id: int) -> None:
    await generic_crud.crud_delete(db, CategoryEntity, CategoryEntity.category_id, category_id)


async def find_by_category_name(db: AsyncSession, category_name: str) -> CategoryEntity | None:
    return await generic_crud.crud_get_by_name(db, CategoryEntity, CategoryEntity.category_name, category_name)


async def find_by_category_id(db: AsyncSession, category_id: int) -> CategoryEntity | None:
    return await generic_crud.crud_get_by_id(db, CategoryEntity, CategoryEntity.category_id, category_id)


async def get_categories(db: AsyncSession, page_number: int, page_size: int) -> PageResult:
    try:
        return await generic_crud.crud_paginate(
            db, CategoryEntity, CategoryEntity.category_id, page_number, page_size
        )
    except Exception as e:
        logger.error("Error processing the get categories page number %s", page_number)
        raise ServiceException(str(e)) from e


async def read_excel_data_to_db(db: AsyncSession, file) -> None:
    try:
        rows = await read_excel_rows(file)
        entities = [
            CategoryEntity(category_name=row[0], category_description=row[1], unrestricted_category=bool(row[2]))
            for row in rows
        ]
        db.add_all(entities)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the read excel account data, message %s", e)
        raise ServiceException(str(e)) from e


async def check_duplicate_record(db: AsyncSession, name: str) -> bool:
    entity = await find_by_category_name(db, name.strip())
    return entity is not None
