from pydantic import BaseModel, Field


class AccountRequestModel(BaseModel):
    model_config = {"populate_by_name": True}

    account_name: str = Field(alias="accountName")
    account_description: str | None = Field(default=None, alias="accountDescription")
    department_id: int | None = Field(default=None, alias="departmentId")


class AccountResponse(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    account_id: int = Field(alias="accountId")
    account_name: str = Field(alias="accountName")
    account_description: str | None = Field(default=None, alias="accountDescription")
    department_id: int | None = Field(default=None, alias="departmentId")
