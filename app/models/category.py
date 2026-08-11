from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoryEntity(Base):
    __tablename__ = "mks_kms_category"

    category_id: Mapped[int] = mapped_column("categoryId", Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column("categoryName", String(255), nullable=False, unique=True)
    category_description: Mapped[str | None] = mapped_column("categoryDescription", String(1000), nullable=True)
    unrestricted_category: Mapped[bool | None] = mapped_column("unrestrictedCategory", Boolean, nullable=True)
