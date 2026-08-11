from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import require_role
from app.schemas.subcategory import SubCategoryRequest, SubCategoryResponse
from app.services import subcategory_service
from app.utils.excel_import import has_excel_format
from app.utils.pagination import page_result_to_dict

NO_CONTENT_MSG = "No sub category found"
ERROR_MSG = "An error occurred while processing the request"

router = APIRouter(prefix="/api/lms/subCategory", tags=["subcategory"], dependencies=[Depends(get_current_user)])

# Restricted to Admin/HR - same rationale as Account Type/Department/Category.
MANAGE_SUBCATEGORIES = [Depends(require_role(Role.ADMIN, Role.HR))]


def _envelope(status_: str, message: str, data=None) -> dict:
    return {"status": status_, "message": message, "data": data}


@router.post("/add", dependencies=MANAGE_SUBCATEGORIES)
async def add_sub_category(payload: SubCategoryRequest, db: AsyncSession = Depends(get_db)):
    if payload is None or not payload.sub_category_name.strip():
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=_envelope("BAD_REQUEST", NO_CONTENT_MSG))
    if await subcategory_service.check_duplicate_record(db, payload.sub_category_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_envelope("BAD_REQUEST", "Sub category name already exists!"),
        )
    sub_category = await subcategory_service.add_sub_category(db, payload)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=_envelope("OK", "Sub category added", sub_category.model_dump(by_alias=True, exclude_none=True)),
    )


@router.put("/edit/{sub_category_id}", dependencies=MANAGE_SUBCATEGORIES)
async def edit_sub_category(sub_category_id: int, payload: SubCategoryRequest, db: AsyncSession = Depends(get_db)):
    if payload is None or sub_category_id <= 0 or not payload.sub_category_name.strip():
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=_envelope("BAD_REQUEST", NO_CONTENT_MSG))
    sub_category = await subcategory_service.edit_sub_category(db, sub_category_id, payload)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=_envelope(
            "OK", "Sub category updated", sub_category.model_dump(by_alias=True, exclude_none=True) if sub_category else None
        ),
    )


@router.delete("/delete/{sub_category_id}", dependencies=MANAGE_SUBCATEGORIES)
async def delete_sub_category_by_id(sub_category_id: int, db: AsyncSession = Depends(get_db)):
    if sub_category_id <= 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=_envelope("BAD_REQUEST", NO_CONTENT_MSG))
    await subcategory_service.delete_sub_category(db, sub_category_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=_envelope("OK", f"Sub category with ID {sub_category_id} deleted"),
    )


@router.get("/subCategories")
async def get_sub_categories(page_number: int = 0, page_size: int = 9999, db: AsyncSession = Depends(get_db)):
    result = await subcategory_service.get_sub_categories(db, page_number, page_size)
    page = page_result_to_dict(
        result, lambda e: SubCategoryResponse.model_validate(e).model_dump(by_alias=True, exclude_none=True)
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=_envelope("OK", "Sub categories found", page))


@router.post("/subCategoryDataImport", dependencies=MANAGE_SUBCATEGORIES)
async def read_excel_data_to_db(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if file is None:
        return JSONResponse(
            status_code=status.HTTP_417_EXPECTATION_FAILED, content=_envelope("EXPECTATION_FAILED", "File not found!")
        )
    if not has_excel_format(file):
        return JSONResponse(
            status_code=status.HTTP_417_EXPECTATION_FAILED,
            content=_envelope("EXPECTATION_FAILED", "Could not upload the file!"),
        )
    await subcategory_service.read_excel_data_to_db(db, file)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=_envelope("OK", f"Uploaded the file successfully: {file.filename}"),
    )


@router.get("/id/{sub_category_id}")
async def find_by_sub_category_id(sub_category_id: int, db: AsyncSession = Depends(get_db)):
    entity = await subcategory_service.find_by_sub_category_id(db, sub_category_id)
    if entity is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=_envelope("NOT_FOUND", "Sub category not found"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=_envelope(
            "OK", "Sub category found", SubCategoryResponse.model_validate(entity).model_dump(by_alias=True, exclude_none=True)
        ),
    )


@router.get("/{sub_category_name}")
async def find_by_sub_category_name(sub_category_name: str, db: AsyncSession = Depends(get_db)):
    if not sub_category_name.strip():
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=_envelope("BAD_REQUEST", NO_CONTENT_MSG))
    entity = await subcategory_service.find_by_sub_category_name(db, sub_category_name)
    if entity is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_envelope("NOT_FOUND", f"Sub category not found with name {sub_category_name}"),
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=_envelope(
            "OK", "Sub category found", SubCategoryResponse.model_validate(entity).model_dump(by_alias=True, exclude_none=True)
        ),
    )
