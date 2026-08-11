from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DepartmentEntity(Base):
    __tablename__ = "mks_kms_department"

    department_id: Mapped[int] = mapped_column("departmentId", Integer, primary_key=True, autoincrement=True)
    department_name: Mapped[str] = mapped_column("departmentName", String(255), nullable=False, unique=True)
    department_description: Mapped[str | None] = mapped_column("departmentDescription", String(1000), nullable=True)
