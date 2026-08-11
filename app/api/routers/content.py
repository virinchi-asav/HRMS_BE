from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.core.deps import LoggedInUser, get_current_user, get_db
from app.core.exceptions import DataNotFoundException, FileAlreadyExistsException
from app.hrms.db import get_hrms_db
from app.schemas.content import EditFileRequest
from app.services import content_service

# The KMS "admin tier" - ADMIN/SUPER_ADMIN roles (BU Head/HR/Manager/Admin map here,
# see HRMS_TO_KMS_ROLE) - the same check `edit_file` already applies. ContentEntity has
# no uploader column to scope a narrower "delete your own upload" rule against.
_FILE_MANAGER_ROLES = (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)

router = APIRouter(prefix="/api/lms", tags=["content"], dependencies=[Depends(get_current_user)])


@router.post("/fileUpload")
async def file_upload(
    dept: int = Form(...),
    account: int = Form(...),
    category: int = Form(...),
    filedesc: str = Form(...),
    user_type: int = Form(...),
    sub_category: int = Form(...),
    doc: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if content_service.is_invalid_file_upload_request(dept, account, category, filedesc, user_type, doc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "BAD_REQUEST", "message": "Invalid Request Fields or FileId"},
        )
    try:
        entity = await content_service.upload_file(db, doc, dept, account, filedesc, category, user_type, sub_category)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "SUCCESS",
                "message": f"File {entity.file_name} uploaded",
                "data": {
                    "fileId": entity.file_id,
                    "fileName": entity.file_name,
                    "fileDescription": entity.file_description,
                    "filePath": entity.file_path,
                    "departmentId": entity.department_id,
                    "accountId": entity.account_id,
                    "categoryId": entity.category_id,
                    "subCategoryId": entity.sub_category_id,
                    "dateTime": entity.date_time.isoformat() if entity.date_time else None,
                    "userType": entity.user_type,
                },
            },
        )
    except DataNotFoundException as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": "NOT_FOUND", "message": str(e)})
    except FileAlreadyExistsException as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "BAD_REQUEST", "message": str(e)})


@router.delete("/remove/{file_id}")
async def remove_file(
    file_id: int,
    current_user: LoggedInUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in _FILE_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to delete this file")
    remove_status = await content_service.remove_file(db, file_id)
    return {"status": remove_status, "message": f"File Removed {remove_status}"}


@router.post("/files/{file_id}/view")
async def record_file_view(
    file_id: int,
    current_user: LoggedInUser = Depends(get_current_user),
    hrms_db: AsyncSession = Depends(get_hrms_db),
):
    """Called once by the frontend each time a user opens a file from the Document
    Library (DocumentLibrary.jsx's openFile) - feeds the Admin Reports "KMS Usage"
    report, the only record of who's actually using this module."""
    await content_service.record_file_view(hrms_db, file_id, current_user.user_id)
    return {"status": "SUCCESS"}


@router.get("/getContentDetails")
async def get_content_details(
    request: Request,
    page_number: int = 0,
    page_size: int = 10,
    category_id: int | None = None,
    department_id: int | None = None,
    account_id: int | None = None,
    name: str | None = None,
    current_user: LoggedInUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    details = await content_service.get_file_content_details(
        db, request, current_user, category_id, department_id, account_id, name
    )
    return [d.model_dump(by_alias=True, exclude_none=True) for d in details]


@router.get("/searchfile/{file_name}")
async def find_by_file_name(
    file_name: str,
    request: Request,
    current_user: LoggedInUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file_name.strip():
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content="FILE NOT FOUND")
    files = await content_service.find_by_file_name(db, request, current_user, file_name)
    return [f.model_dump(by_alias=True, exclude_none=True) for f in files]


@router.post("/editfile/{file_id}")
async def edit_file(
    file_id: int,
    edit_request: EditFileRequest,
    current_user: LoggedInUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if content_service.is_invalid_edit_file_request(file_id, edit_request):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "BAD_REQUEST", "message": "Invalid Request Fields or FileId"},
        )
    response = await content_service.edit_file(db, file_id, edit_request, current_user)
    # Matches FileUploadController.editFile: always HTTP 202, regardless of outcome.
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response)
