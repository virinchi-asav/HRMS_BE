from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class DefaultResponse(BaseModel):
    """Mirrors com.mks.lms.model.DefaultResponse - generic envelope, null fields omitted.

    Routes returning this should be declared with response_model_exclude_none=True.
    """

    status: str | None = None
    message: str | None = None
    data: Any | None = None


class MessageResponse(BaseModel):
    message: str


class ChangePasswordResponse(BaseModel):
    message: str
    status: str


class PageResponse(BaseModel, Generic[T]):
    """Mirrors the JSON shape of Spring Data's Page<T> (the fields the existing frontend
    is expected to actually consume - content/totalElements/totalPages/number/size)."""

    content: list[T]
    total_elements: int = Field(alias="totalElements")
    total_pages: int = Field(alias="totalPages")
    size: int
    number: int
    number_of_elements: int = Field(alias="numberOfElements")
    first: bool
    last: bool
    empty: bool

    model_config = {"populate_by_name": True}
