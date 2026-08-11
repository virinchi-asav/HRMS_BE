from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import DepartmentEntity
from app.schemas.department import DepartmentRequest
from app.services import generic_crud
from app.utils.excel_import import read_excel_rows
from app.utils.pagination import PageResult

# NOTE: unlike account/category/subcategory, DepartmentServiceImpl in the Java app does
# NOT wrap exceptions in ServiceException - they propagate to the generic 500 handler.
# That inconsistency is intentionally preserved here (no try/except around DB calls).


async def save_department(db: AsyncSession, data: DepartmentRequest) -> None:
    entity = DepartmentEntity(
        department_name=data.department_name,
        department_description=data.department_description,
    )
    db.add(entity)
    await db.commit()


async def update_department(db: AsyncSession, data: DepartmentRequest, department_id: int) -> None:
    entity = await generic_crud.crud_get_by_id(db, DepartmentEntity, DepartmentEntity.department_id, department_id)
    if entity is not None:
        entity.department_name = data.department_name
        entity.department_description = data.department_description
        await db.commit()


async def delete_department(db: AsyncSession, department_id: int) -> None:
    await generic_crud.crud_delete(db, DepartmentEntity, DepartmentEntity.department_id, department_id)


async def get_departments(db: AsyncSession, page_number: int, page_size: int) -> PageResult:
    return await generic_crud.crud_paginate(
        db,
        DepartmentEntity,
        DepartmentEntity.department_id,
        page_number,
        page_size,
        exclude_sentinel_col=DepartmentEntity.department_id,
    )


async def find_by_department_name(db: AsyncSession, department_name: str) -> DepartmentEntity | None:
    return await generic_crud.crud_get_by_name(db, DepartmentEntity, DepartmentEntity.department_name, department_name)


async def find_by_id(db: AsyncSession, department_id: int) -> DepartmentEntity | None:
    return await generic_crud.crud_get_by_id(db, DepartmentEntity, DepartmentEntity.department_id, department_id)


async def read_excel_data_to_db(db: AsyncSession, file) -> None:
    from app.core.exceptions import ServiceException

    try:
        rows = await read_excel_rows(file)
    except Exception as e:  # only the file-parsing step is wrapped in Java (IOException)
        raise ServiceException(str(e)) from e

    entities = [
        DepartmentEntity(department_name=row[0], department_description=row[1])
        for row in rows
    ]
    db.add_all(entities)
    await db.commit()
