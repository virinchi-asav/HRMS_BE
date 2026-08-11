import logging
from datetime import datetime
from pathlib import Path

from fastapi import Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import CONFIDENTIAL_DEPARTMENT_NAME, UserRole
from app.core.deps import LoggedInUser
from app.core.exceptions import DataNotFoundException, FileAlreadyExistsException
from app.hrms.models.kms_file_view import KmsFileViewEntity
from app.models.content import ContentEntity
from app.schemas.content import ContentDetails, EditFileRequest, FileDetails
from app.services import (
    account_service,
    category_service,
    department_service,
    file_storage_service,
    generic_crud,
    subcategory_service,
    user_type_service,
)
from app.utils.privilege import is_user_privileged
from app.utils.sentinel import is_sentinel
from app.utils.url_rewrite import build_public_url

logger = logging.getLogger(__name__)


def is_invalid_file_upload_request(
    dept: int | None, account: int | None, category: int | None, file_description: str | None,
    user_type: int | None, file: UploadFile | None,
) -> bool:
    """Mirrors FileValidator.isInvalidFileUploadRequest.

    Note the asymmetry: dept/account allow the sentinel 0 ("All"), category/userType do not.
    """
    return (
        dept is None or dept < 0
        or account is None or account < 0
        or category is None or category <= 0
        or user_type is None or user_type <= 0
        or file is None
        or not (file_description and file_description.strip())
    )


def is_invalid_edit_file_request(file_id: int | None, edit_request: EditFileRequest | None) -> bool:
    """Mirrors FileValidator.isValidRequest (misleadingly named - true means invalid)."""
    return (
        file_id is None or file_id <= 0
        or edit_request is None
        or not (edit_request.file_desc and edit_request.file_desc.strip())
    )


async def upload_file(
    db: AsyncSession,
    file: UploadFile,
    dept: int,
    account: int,
    desc: str,
    category: int,
    user_type: int,
    sub_category: int,
) -> ContentEntity:
    """dept/account may be the sentinel 0 ("All") per is_invalid_file_upload_request's
    own docstring - that's not a real department/account row, so it's exempted from the
    existence check below (and given a literal "All" path segment instead of a name
    looked up from a nonexistent row). sub_category is genuinely optional (the
    column is nullable, and the request validator never requires it) - 0/absent means
    "no sub-folder", not an id to look up."""
    file_name = file.filename

    account_entity = None if is_sentinel(account) else await account_service.find_by_account_id(db, account)
    department_entity = None if is_sentinel(dept) else await department_service.find_by_id(db, dept)
    category_entity = await category_service.find_by_category_id(db, category)
    sub_category_entity = (
        await subcategory_service.find_by_sub_category_id(db, sub_category) if sub_category else None
    )

    if (
        (not is_sentinel(dept) and department_entity is None)
        or (not is_sentinel(account) and account_entity is None)
        or category_entity is None
        or (sub_category and sub_category_entity is None)
    ):
        raise DataNotFoundException("Invalid ID")

    file_path = file_storage_service.build_content_path(
        settings.file_storage_root,
        department_entity.department_name if department_entity else "All",
        account_entity.account_name if account_entity else "All",
        category_entity.category_name,
        sub_category_entity.sub_category_name if sub_category_entity else "General",
        file_name,
    )

    existing = await db.execute(select(ContentEntity).where(ContentEntity.file_path == str(file_path)))
    if existing.scalar_one_or_none() is not None:
        raise FileAlreadyExistsException(f"{file_name} already exists")

    content = await file.read()
    await file_storage_service.write_file(file_path, content)

    sub_category_id = sub_category_entity.sub_category_id if sub_category_entity else None

    dup_stmt = select(ContentEntity).where(
        ContentEntity.department_id == dept,
        ContentEntity.account_id == account,
        ContentEntity.category_id == category,
        ContentEntity.sub_category_id == sub_category_id,
        ContentEntity.file_name == file_name,
    )
    existing_row = (await db.execute(dup_stmt)).scalars().first()

    if existing_row is not None:
        entity = existing_row
        entity.file_description = desc
        entity.file_path = str(file_path)
        entity.user_type = user_type
    else:
        entity = ContentEntity(
            account_id=account,
            department_id=dept,
            category_id=category,
            sub_category_id=sub_category_id,
            file_description=desc,
            file_name=file_name,
            file_path=str(file_path),
            user_type=user_type,
        )
        db.add(entity)

    entity.date_time = datetime.utcnow()
    await db.commit()
    await db.refresh(entity)
    return entity


async def remove_file(db: AsyncSession, file_id: int) -> str:
    """Returns "Success" / "Failed" / "" (empty on disk-delete error) - mirrors
    FileUploadImpl.removeFile's exact three-way outcome, including the empty-string case
    that leaves the DB row untouched when the on-disk delete fails."""
    entity = await generic_crud.crud_get_by_id(db, ContentEntity, ContentEntity.file_id, file_id)
    if entity is None:
        return "Failed"
    try:
        Path(entity.file_path).unlink()
    except OSError as e:
        logger.error("Exception occurred while removing file: %s", e)
        return ""
    await db.delete(entity)
    await db.commit()
    return "Success"


def _relative_to_root(file_path: str) -> str:
    """Strips the configured storage root off an absolute on-disk path so it can be
    turned into a public URL. Uses pathlib (not a raw string prefix check) so it's
    immune to backslash-vs-forward-slash / trailing-separator differences between how
    the root is configured and how paths were actually joined when writing the file."""
    try:
        root = Path(settings.file_storage_root).resolve()
        return str(Path(file_path).resolve().relative_to(root))
    except (ValueError, OSError):
        return file_path


async def _map_to_file_details(db: AsyncSession, request: Request, entity: ContentEntity) -> FileDetails:
    account_entity = await account_service.find_by_account_id(db, entity.account_id)
    department_entity = await department_service.find_by_id(db, entity.department_id)
    sub_category_entity = await subcategory_service.find_by_sub_category_id(db, entity.sub_category_id)
    category_entity = await category_service.find_by_category_id(db, entity.category_id)
    user_type_entity = await user_type_service.find_by_user_type_id(db, entity.user_type)

    public_url = build_public_url(request, _relative_to_root(entity.file_path or ""))

    return FileDetails(
        file_id=entity.file_id,
        file_name=entity.file_name,
        file_description=entity.file_description,
        file_path=public_url,
        department_id=entity.department_id,
        department=department_entity.department_name if department_entity else None,
        account_id=entity.account_id,
        account=account_entity.account_name if account_entity else None,
        category_id=entity.category_id,
        category=category_entity.category_name if category_entity else None,
        sub_category_id=entity.sub_category_id,
        sub_category=sub_category_entity.sub_category_name if sub_category_entity else None,
        date_time=entity.date_time,
        user_type_id=entity.user_type,
        user_type=user_type_entity.type_name if user_type_entity else None,
    )


async def _confidential_department_id(db: AsyncSession) -> int | None:
    confidential_dept = await department_service.find_by_department_name(db, CONFIDENTIAL_DEPARTMENT_NAME)
    return confidential_dept.department_id if confidential_dept else None


async def _visibility_checker(db: AsyncSession, current_user: LoggedInUser):
    """A single-entity version of the access rules `get_file_content_details` applies to
    its listing (confidential-department allow-list, user-type match, own department/
    account unless privileged) - used by `find_by_file_name`, which previously returned
    search results with no visibility filtering at all."""
    confidential_dept_id = await _confidential_department_id(db)
    privileged = is_user_privileged(current_user.role, current_user.user_type_id)

    def _visible(entity: ContentEntity) -> bool:
        if confidential_dept_id is not None and entity.department_id == confidential_dept_id:
            if current_user.email not in settings.confidential_file_users_list:
                return False
        if not (privileged or entity.user_type == current_user.user_type_id):
            return False
        if privileged:
            return True
        return (entity.department_id == current_user.department_id or is_sentinel(entity.department_id)) and (
            entity.account_id == current_user.account_id or is_sentinel(entity.account_id)
        )

    return _visible


async def get_file_content_details(
    db: AsyncSession,
    request: Request,
    current_user: LoggedInUser,
    category_id: int | None,
    department_id: int | None,
    account_id: int | None,
    name: str | None,
) -> list[ContentDetails]:
    result = await db.execute(select(ContentEntity).order_by(ContentEntity.file_id.desc()))
    all_content = result.scalars().all()

    confidential_dept_id = await _confidential_department_id(db)
    privileged = is_user_privileged(current_user.role, current_user.user_type_id)

    def is_confidential_ok(entity: ContentEntity) -> bool:
        if confidential_dept_id is not None and entity.department_id == confidential_dept_id:
            return current_user.email in settings.confidential_file_users_list
        return True

    def is_user_type_ok(entity: ContentEntity) -> bool:
        return privileged or entity.user_type == current_user.user_type_id

    def is_department_ok(entity: ContentEntity) -> bool:
        if current_user.role == UserRole.SUPER_ADMIN.value:
            return department_id is None or entity.department_id == department_id
        if privileged:
            return True
        return entity.department_id == current_user.department_id or is_sentinel(entity.department_id)

    def is_account_ok(entity: ContentEntity) -> bool:
        if current_user.role == UserRole.SUPER_ADMIN.value:
            return account_id is None or entity.account_id == account_id
        if privileged:
            return True
        return entity.account_id == current_user.account_id or is_sentinel(entity.account_id)

    def is_category_ok(entity: ContentEntity) -> bool:
        return category_id is None or entity.category_id == category_id

    def matches_name(entity: ContentEntity) -> bool:
        return name is None or (entity.file_name is not None and name.lower() in entity.file_name.lower())

    filtered = [
        e
        for e in all_content
        if is_confidential_ok(e)
        and is_user_type_ok(e)
        and is_department_ok(e)
        and is_account_ok(e)
        and is_category_ok(e)
        and matches_name(e)
    ]

    grouped: dict[int, dict[int, dict[int, list[ContentEntity]]]] = {}
    for entity in filtered:
        grouped.setdefault(entity.account_id, {}).setdefault(entity.department_id, {}).setdefault(
            entity.category_id, []
        ).append(entity)

    result_list: list[ContentDetails] = []
    for acc_id, dept_map in grouped.items():
        for dept_id, cat_map in dept_map.items():
            for cat_id, entities in cat_map.items():
                file_details = [await _map_to_file_details(db, request, e) for e in entities]
                result_list.append(
                    ContentDetails(
                        department_id=dept_id, account_id=acc_id, category_id=cat_id, lms_content=file_details
                    )
                )
    return result_list


async def find_by_file_name(
    db: AsyncSession, request: Request, current_user: LoggedInUser, name: str
) -> list[FileDetails]:
    result = await db.execute(select(ContentEntity).where(ContentEntity.file_name.ilike(f"%{name}%")))
    entities = result.scalars().all()
    is_visible = await _visibility_checker(db, current_user)
    return [await _map_to_file_details(db, request, e) for e in entities if is_visible(e)]


async def edit_file(
    db: AsyncSession, file_id: int, edit_request: EditFileRequest, current_user: LoggedInUser
) -> dict:
    """Returns a DefaultResponse-shaped dict; the router always answers HTTP 202
    regardless of which branch below is hit - matching FileUploadController.editFile."""
    if current_user.role not in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value):
        return {"status": "USER_NOT_ALLOWED", "message": "User not allowed to edit File"}

    entity = await generic_crud.crud_get_by_id(db, ContentEntity, ContentEntity.file_id, file_id)
    account_entity = None if is_sentinel(edit_request.account) else await account_service.find_by_account_id(db, edit_request.account)
    department_entity = None if is_sentinel(edit_request.dept) else await department_service.find_by_id(db, edit_request.dept)
    category_entity = await category_service.find_by_category_id(db, edit_request.category)
    user_type_entity = await user_type_service.find_by_user_type_id(db, edit_request.user_type)

    if (
        entity is None
        or category_entity is None
        or user_type_entity is None
        or (not is_sentinel(edit_request.dept) and department_entity is None)
        or (not is_sentinel(edit_request.account) and account_entity is None)
    ):
        return {"status": "DATA_NOT_EXIST", "message": "User Requested filedata not exist"}

    if (
        edit_request.category != entity.category_id
        or edit_request.account != entity.account_id
        or edit_request.dept != entity.department_id
    ):
        old_path = Path(entity.file_path)
        file_name = entity.file_name
        new_dir = file_storage_service.build_edit_dir(
            settings.file_storage_root,
            department_entity.department_name if department_entity else "All",
            account_entity.account_name if account_entity else "All",
            category_entity.category_name,
        )
        new_path = new_dir / file_name
        await file_storage_service.move_file(old_path, new_path)

        entity.account_id = edit_request.account
        entity.category_id = edit_request.category
        entity.department_id = edit_request.dept
        entity.file_path = str(new_path)

    entity.file_description = edit_request.file_desc
    entity.user_type = edit_request.user_type
    await db.commit()

    return {"status": "FILE_EDITED_SUCCESSFUL", "message": "File edited successfully"}


async def record_file_view(hrms_db: AsyncSession, file_id: int, user_id: int) -> None:
    """Logs one KMS Document Library file-open event, for the Admin Reports "who's
    actively using KMS" report (app.hrms.services.reports_service.get_kms_usage_report).
    Written to the HRMS database (not this KMS one) since that's where every other new
    feature table lives - file_id is a plain, cross-database reference to this module's
    own ContentEntity.file_id, same convention as TrainingProgramEntity.account_id."""
    hrms_db.add(KmsFileViewEntity(file_id=file_id, user_id=user_id, viewed_at=datetime.utcnow()))
    await hrms_db.commit()
