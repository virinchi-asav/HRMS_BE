from pydantic import BaseModel, Field


class DepartmentRequest(BaseModel):
    model_config = {"populate_by_name": True}

    department_name: str = Field(alias="departmentName")
    department_description: str | None = Field(default=None, alias="departmentDescription")


class DepartmentResponse(BaseModel):
    """Mirrors LmsDepartmentEntity, returned as-is by DepartmentServiceImpl."""

    model_config = {"populate_by_name": True, "from_attributes": True}

    department_id: int = Field(alias="departmentId")
    department_name: str = Field(alias="departmentName")
    department_description: str | None = Field(default=None, alias="departmentDescription")
