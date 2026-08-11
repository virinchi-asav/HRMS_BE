from datetime import datetime

from pydantic import BaseModel, Field


class EditFileRequest(BaseModel):
    model_config = {"populate_by_name": True}

    dept: int
    account: int
    category: int
    file_desc: str = Field(alias="fileDesc")
    user_type: int = Field(alias="userType")


class FileDetails(BaseModel):
    model_config = {"populate_by_name": True}

    file_id: int = Field(alias="fileId")
    file_name: str | None = Field(default=None, alias="fileName")
    file_description: str | None = Field(default=None, alias="fileDescription")
    file_path: str | None = Field(default=None, alias="filePath")
    department_id: int | None = Field(default=None, alias="departmentId")
    department: str | None = None
    account_id: int | None = Field(default=None, alias="accountId")
    account: str | None = None
    category_id: int | None = Field(default=None, alias="categoryId")
    category: str | None = None
    sub_category_id: int | None = Field(default=None, alias="subCategoryId")
    sub_category: str | None = Field(default=None, alias="subCategory")
    date_time: datetime | None = Field(default=None, alias="dateTime")
    user_type_id: int | None = Field(default=None, alias="userTypeId")
    user_type: str | None = Field(default=None, alias="userType")


class ContentDetails(BaseModel):
    model_config = {"populate_by_name": True}

    department_id: int | None = Field(default=None, alias="departmentId")
    account_id: int | None = Field(default=None, alias="accountId")
    category_id: int | None = Field(default=None, alias="categoryId")
    lms_content: list[FileDetails] = Field(default_factory=list, alias="lmsContent")
