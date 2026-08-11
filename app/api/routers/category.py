from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import require_role
from app.schemas.category import CategoryRequestModel, CategoryResponse
from app.schemas.common import MessageResponse
from app.services import category_service
from app.utils.excel_import import has_excel_format
from app.utils.pagination import page_result_to_dict

router = APIRouter(prefix="/api/lms/category", tags=["category"], dependencies=[Depends(get_current_user)])

# Restricted to Admin/HR - same rationale as Account Type/Department: this taxonomy is
# shared structural data, not a per-user setting.
MANAGE_CATEGORIES = [Depends(require_role(Role.ADMIN, Role.HR))]


@router.post("/add", dependencies=MANAGE_CATEGORIES)
async def add_category(payload: CategoryRequestModel, db: AsyncSession = Depends(get_db)):
    if payload is None or not payload.category_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    if await category_service.check_duplicate_record(db, payload.category_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=MessageResponse(message="Category name already exist!").model_dump(),
        )
    await category_service.add_category(db, payload)
    return JSONResponse(status_code=status.HTTP_200_OK, content="CREATED")


@router.put("/edit/{category_id}", dependencies=MANAGE_CATEGORIES)
async def edit_category(category_id: int, payload: CategoryRequestModel, db: AsyncSession = Depends(get_db)):
    if payload is None or category_id <= 0 or not payload.category_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await category_service.edit_category(db, category_id, payload)
    return JSONResponse(status_code=status.HTTP_200_OK, content="OK")


@router.delete("/delete/{category_id}", dependencies=MANAGE_CATEGORIES)
async def delete_category_by_id(category_id: int, db: AsyncSession = Depends(get_db)):
    if category_id <= 0:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await category_service.delete_category(db, category_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content="OK")


@router.get("/categories")
async def get_categories(page_number: int = 0, page_size: int = 9999, db: AsyncSession = Depends(get_db)):
    result = await category_service.get_categories(db, page_number, page_size)
    return page_result_to_dict(
        result, lambda e: CategoryResponse.model_validate(e).model_dump(by_alias=True, exclude_none=True)
    )


@router.post("/categoryDataImport", dependencies=MANAGE_CATEGORIES)
async def read_excel_data_to_db(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if file is None:
        return JSONResponse(status_code=status.HTTP_417_EXPECTATION_FAILED, content={"message": "File Not found !"})
    if not has_excel_format(file):
        return JSONResponse(
            status_code=status.HTTP_417_EXPECTATION_FAILED, content={"message": "Could not upload the file: !"}
        )
    await category_service.read_excel_data_to_db(db, file)
    return JSONResponse(status_code=status.HTTP_200_OK, content=f"Uploaded the file successfully: {file.filename}")


@router.get("/id/{category_id}")
async def find_by_category_id(category_id: int, db: AsyncSession = Depends(get_db)):
    entity = await category_service.find_by_category_id(db, category_id)
    if entity is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=None)
    return CategoryResponse.model_validate(entity).model_dump(by_alias=True, exclude_none=True)


@router.get("/{category_name}")
async def find_by_category_name(category_name: str, db: AsyncSession = Depends(get_db)):
    if not category_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    entity = await category_service.find_by_category_name(db, category_name)
    if entity is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=None)
    return CategoryResponse.model_validate(entity).model_dump(by_alias=True, exclude_none=True)
