from pydantic import BaseModel, Field


class SubCategoryRequest(BaseModel):
    """account_id/category_id are accepted for wire compatibility but - matching the
    original SubCategoryServiceImpl - are never persisted/used."""

    model_config = {"populate_by_name": True}

    sub_category_name: str = Field(alias="subCategoryName")
    sub_category_description: str | None = Field(default=None, alias="subCategoryDescription")
    account_id: int | None = Field(default=None, alias="accountId")
    category_id: int | None = Field(default=None, alias="categoryId")


class SubCategoryResponse(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    sub_category_id: int = Field(alias="subCategoryId")
    sub_category_name: str = Field(alias="subCategoryName")
    sub_category_description: str | None = Field(default=None, alias="subCategoryDescription")
