from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.hrms.core.constants import Role
from app.hrms.core.deps import require_role
from app.schemas.department import DepartmentRequest, DepartmentResponse
from app.services import department_service
from app.utils.pagination import page_result_to_dict

router = APIRouter(prefix="/api/lms/department", tags=["department"], dependencies=[Depends(get_current_user)])

# Restricted to Admin/HR - the department taxonomy feeds KMS content scoping and user
# org-structure fields, so an unauthorized edit ripples further than it looks.
MANAGE_DEPARTMENTS = [Depends(require_role(Role.ADMIN, Role.HR))]


@router.post("/add", dependencies=MANAGE_DEPARTMENTS)
async def add_department(payload: DepartmentRequest, db: AsyncSession = Depends(get_db)):
    if payload is None or not payload.department_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await department_service.save_department(db, payload)
    return JSONResponse(status_code=status.HTTP_200_OK, content="CREATED")


@router.put("/edit/{department_id}", dependencies=MANAGE_DEPARTMENTS)
async def edit_department(department_id: int, payload: DepartmentRequest, db: AsyncSession = Depends(get_db)):
    if payload is None or not (payload.department_name and payload.department_name.strip()):
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await department_service.update_department(db, payload, department_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content="OK")


@router.get("/departments")
async def get_departments(page_number: int = 0, page_size: int = 9999, db: AsyncSession = Depends(get_db)):
    result = await department_service.get_departments(db, page_number, page_size)
    return page_result_to_dict(
        result, lambda e: DepartmentResponse.model_validate(e).model_dump(by_alias=True, exclude_none=True)
    )


@router.delete("/delete/{department_id}", dependencies=MANAGE_DEPARTMENTS)
async def delete_department_by_id(department_id: int, db: AsyncSession = Depends(get_db)):
    if department_id <= 0:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    await department_service.delete_department(db, department_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content="OK")


@router.post("/departmentDataImport", dependencies=MANAGE_DEPARTMENTS)
async def read_excel_data_to_db(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if file is None:
        return JSONResponse(status_code=status.HTTP_417_EXPECTATION_FAILED, content="File Not found !")
    await department_service.read_excel_data_to_db(db, file)
    return JSONResponse(status_code=status.HTTP_200_OK, content=f"Uploaded the file successfully: {file.filename}")


@router.get("/{department_id}")
async def find_by_id(department_id: int, db: AsyncSession = Depends(get_db)):
    entity = await department_service.find_by_id(db, department_id)
    return DepartmentResponse.model_validate(entity).model_dump(by_alias=True, exclude_none=True) if entity else None
