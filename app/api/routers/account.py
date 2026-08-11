from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import require_role
from app.schemas.account import AccountRequestModel
from app.schemas.common import MessageResponse
from app.services import account_service
from app.utils.excel_import import has_excel_format
from app.utils.pagination import page_result_to_dict

NO_CONTENT_MSG = "No content found"

router = APIRouter(prefix="/api/lms/account", tags=["account"], dependencies=[Depends(get_current_user)])

# Account Type is referenced across Question Banks, Trainee filtering, and KMS content
# scoping - previously any authenticated user (including Candidate) could create/edit/
# delete it. Restricted to Admin/HR, consistent with Question Bank and User Management.
MANAGE_ACCOUNTS = [Depends(require_role(Role.ADMIN, Role.HR))]


@router.post("/add", dependencies=MANAGE_ACCOUNTS)
async def add_account(payload: AccountRequestModel, db: AsyncSession = Depends(get_db)):
    if payload is None or not payload.account_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    if await account_service.check_duplicate_record(db, payload.account_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=MessageResponse(message="Account name already exist!").model_dump(),
        )
    await account_service.add_account(db, payload)
    return JSONResponse(status_code=status.HTTP_200_OK, content="CREATED")


@router.put("/edit/{account_id}", dependencies=MANAGE_ACCOUNTS)
async def edit_account(account_id: int, payload: AccountRequestModel, db: AsyncSession = Depends(get_db)):
    if payload is None or account_id <= 0 or not payload.account_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await account_service.edit_account(db, account_id, payload)
    return JSONResponse(status_code=status.HTTP_200_OK, content="OK")


@router.delete("/delete/{account_id}", dependencies=MANAGE_ACCOUNTS)
async def delete_account_by_id(account_id: int, db: AsyncSession = Depends(get_db)):
    if account_id <= 0:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await account_service.delete_account(db, account_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content="OK")


@router.get("/accounts")
async def get_accounts(page_number: int = 0, page_size: int = 9999, db: AsyncSession = Depends(get_db)):
    result = await account_service.get_accounts(db, page_number, page_size)
    return page_result_to_dict(result, lambda a: a.model_dump(by_alias=True, exclude_none=True))


@router.post("/accountDataImport", dependencies=MANAGE_ACCOUNTS)
async def read_excel_data_to_db(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if file is None:
        return JSONResponse(status_code=status.HTTP_417_EXPECTATION_FAILED, content={"message": "File Not found !"})
    if not has_excel_format(file):
        return JSONResponse(
            status_code=status.HTTP_417_EXPECTATION_FAILED, content={"message": "Could not upload the file: !"}
        )
    await account_service.read_excel_data_to_db(db, file)
    return JSONResponse(status_code=status.HTTP_200_OK, content=f"Uploaded the file successfully: {file.filename}")


@router.get("/department/{department_id}")
async def find_accounts_by_department(department_id: int, db: AsyncSession = Depends(get_db)):
    accounts = await account_service.get_accounts_by_department(db, department_id)
    return [a.model_dump(by_alias=True, exclude_none=True) for a in accounts]


@router.get("/id/{account_id}")
async def find_by_account_id(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await account_service.find_account_by_account_id(db, account_id)
    if account is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=None)
    return account.model_dump(by_alias=True, exclude_none=True)


@router.get("/{account_name}")
async def find_by_account_name(account_name: str, db: AsyncSession = Depends(get_db)):
    if not account_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    account = await account_service.find_by_account_name(db, account_name)
    if account is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=None)
    return account.model_dump(by_alias=True, exclude_none=True)
