from pydantic import BaseModel, Field


class CategoryRequestModel(BaseModel):
    model_config = {"populate_by_name": True}

    category_name: str = Field(alias="categoryName")
    category_description: str | None = Field(default=None, alias="categoryDescription")
    unrestricted_category: bool | None = Field(default=None, alias="unrestrictedCategory")


class CategoryResponse(BaseModel):
    """Mirrors LmsCategoryEntity, returned as-is (no separate DTO) by CategoryServiceImpl."""

    model_config = {"populate_by_name": True, "from_attributes": True}

    category_id: int = Field(alias="categoryId")
    category_name: str = Field(alias="categoryName")
    category_description: str | None = Field(default=None, alias="categoryDescription")
    unrestricted_category: bool | None = Field(default=None, alias="unrestrictedCategory")
