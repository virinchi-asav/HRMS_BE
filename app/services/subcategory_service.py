import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceException
from app.models.subcategory import SubCategoryEntity
from app.schemas.subcategory import SubCategoryRequest, SubCategoryResponse
from app.services import generic_crud
from app.utils.excel_import import read_excel_rows
from app.utils.pagination import PageResult

logger = logging.getLogger(__name__)


def _to_response(entity: SubCategoryEntity) -> SubCategoryResponse:
    return SubCategoryResponse.model_validate(entity)


async def add_sub_category(db: AsyncSession, data: SubCategoryRequest) -> SubCategoryResponse:
    try:
        entity = SubCategoryEntity(
            sub_category_name=data.sub_category_name,
            sub_category_description=data.sub_category_description,
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
        return _to_response(entity)
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the add sub category name %s", data.sub_category_name)
        raise ServiceException(str(e)) from e


async def edit_sub_category(db: AsyncSession, sub_category_id: int, data: SubCategoryRequest) -> SubCategoryResponse | None:
    try:
        entity = await generic_crud.crud_get_by_id(
            db, SubCategoryEntity, SubCategoryEntity.sub_category_id, sub_category_id
        )
        if entity is None:
            return None
        entity.sub_category_name = data.sub_category_name
        entity.sub_category_description = data.sub_category_description
        await db.commit()
        await db.refresh(entity)
        return _to_response(entity)
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the edit sub category name %s", data.sub_category_name)
        raise ServiceException(str(e)) from e


async def delete_sub_category(db: AsyncSession, sub_category_id: int) -> None:
    await generic_crud.crud_delete(db, SubCategoryEntity, SubCategoryEntity.sub_category_id, sub_category_id)


async def find_by_sub_category_name(db: AsyncSession, name: str) -> SubCategoryEntity | None:
    return await generic_crud.crud_get_by_name(db, SubCategoryEntity, SubCategoryEntity.sub_category_name, name)


async def find_by_sub_category_id(db: AsyncSession, sub_category_id: int) -> SubCategoryEntity | None:
    return await generic_crud.crud_get_by_id(db, SubCategoryEntity, SubCategoryEntity.sub_category_id, sub_category_id)


async def get_sub_categories(db: AsyncSession, page_number: int, page_size: int) -> PageResult:
    return await generic_crud.crud_paginate(
        db, SubCategoryEntity, SubCategoryEntity.sub_category_id, page_number, page_size
    )


async def read_excel_data_to_db(db: AsyncSession, file) -> None:
    try:
        rows = await read_excel_rows(file)
        entities = [
            SubCategoryEntity(sub_category_name=row[0], sub_category_description=row[1]) for row in rows
        ]
        db.add_all(entities)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the read excel sub category data, message %s", e)
        raise ServiceException(str(e)) from e


async def check_duplicate_record(db: AsyncSession, name: str) -> bool:
    entity = await find_by_sub_category_name(db, name.strip())
    return entity is not None
