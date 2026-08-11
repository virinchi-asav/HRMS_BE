import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SENTINEL_ID
from app.core.exceptions import ServiceException
from app.models.account import AccountEntity
from app.schemas.account import AccountRequestModel, AccountResponse
from app.services import department_service, generic_crud
from app.utils.excel_import import read_excel_rows
from app.utils.pagination import PageResult

logger = logging.getLogger(__name__)


def _to_response(entity: AccountEntity) -> AccountResponse:
    return AccountResponse.model_validate(entity)


async def add_account(db: AsyncSession, data: AccountRequestModel) -> None:
    try:
        entity = AccountEntity(
            account_name=data.account_name,
            account_description=data.account_description,
            department_id=data.department_id,
        )
        db.add(entity)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the add account name %s", data.account_name)
        raise ServiceException(str(e)) from e


async def edit_account(db: AsyncSession, account_id: int, data: AccountRequestModel) -> None:
    try:
        entity = await generic_crud.crud_get_by_id(db, AccountEntity, AccountEntity.account_id, account_id)
        if entity is not None:
            entity.account_name = data.account_name
            entity.department_id = data.department_id
            entity.account_description = data.account_description
            await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the edit account name %s", data.account_name)
        raise ServiceException(str(e)) from e


async def delete_account(db: AsyncSession, account_id: int) -> None:
    await generic_crud.crud_delete(db, AccountEntity, AccountEntity.account_id, account_id)


async def find_account_by_name(db: AsyncSession, account_name: str) -> AccountEntity | None:
    return await generic_crud.crud_get_by_name(db, AccountEntity, AccountEntity.account_name, account_name)


async def find_by_account_name(db: AsyncSession, account_name: str) -> AccountResponse | None:
    entity = await find_account_by_name(db, account_name)
    return _to_response(entity) if entity else None


async def get_accounts(db: AsyncSession, page_number: int, page_size: int) -> PageResult:
    try:
        result = await generic_crud.crud_paginate(
            db,
            AccountEntity,
            AccountEntity.account_id,
            page_number,
            page_size,
            exclude_sentinel_col=AccountEntity.account_id,
        )
        result.items = [_to_response(e) for e in result.items]
        return result
    except Exception as e:
        logger.error("Error processing the get accounts page number %s", page_number)
        raise ServiceException(str(e)) from e


async def read_excel_data_to_db(db: AsyncSession, file) -> None:
    try:
        rows = await read_excel_rows(file)
        entities = []
        for row in rows:
            account_name, account_description, department_name = row[0], row[1], row[2]
            department = await department_service.find_by_department_name(db, department_name)
            entities.append(
                AccountEntity(
                    account_name=account_name,
                    account_description=account_description,
                    department_id=department.department_id if department else None,
                )
            )
        db.add_all(entities)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Error processing the read excel account data, message %s", e)
        raise ServiceException(str(e)) from e


async def check_duplicate_record(db: AsyncSession, name: str) -> bool:
    try:
        account = await find_by_account_name(db, name.strip())
        return account is not None
    except Exception as e:
        logger.error("Error processing the check Duplicate Record on name %s", name)
        raise ServiceException(str(e)) from e


async def get_accounts_by_department(db: AsyncSession, department_id: int) -> list[AccountResponse]:
    try:
        stmt = select(AccountEntity).where(
            AccountEntity.department_id == department_id,
            AccountEntity.department_id != SENTINEL_ID,
        )
        result = await db.execute(stmt)
        return [_to_response(e) for e in result.scalars().all()]
    except Exception as e:
        logger.error("Error processing the get accounts by department %s", department_id)
        raise ServiceException(str(e)) from e


async def find_by_account_id(db: AsyncSession, account_id: int) -> AccountEntity | None:
    return await generic_crud.crud_get_by_id(db, AccountEntity, AccountEntity.account_id, account_id)


async def find_account_by_account_id(db: AsyncSession, account_id: int) -> AccountResponse | None:
    entity = await find_by_account_id(db, account_id)
    return _to_response(entity) if entity else None


BENCH_ACCOUNT_NAME = "Bench"


async def get_or_create_bench_account(db: AsyncSession) -> AccountEntity:
    """The default Account Type for employees not currently allocated to a client
    account/department - guaranteed to exist (called from the app startup lifespan),
    so any code defaulting a user's account_type to Bench, or any Account Type
    dropdown, can rely on it always being present."""
    entity = await find_account_by_name(db, BENCH_ACCOUNT_NAME)
    if entity is not None:
        return entity
    entity = AccountEntity(account_name=BENCH_ACCOUNT_NAME, account_description="Not currently allocated to a client account")
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity
