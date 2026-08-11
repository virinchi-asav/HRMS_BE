from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SubCategoryEntity(Base):
    __tablename__ = "mks_kms_subcategory"

    sub_category_id: Mapped[int] = mapped_column("subCategoryId", Integer, primary_key=True, autoincrement=True)
    sub_category_name: Mapped[str] = mapped_column("subCategoryName", String(255), nullable=False, unique=True)
    sub_category_description: Mapped[str | None] = mapped_column(
        "subCategoryDescription", String(1000), nullable=True
    )
