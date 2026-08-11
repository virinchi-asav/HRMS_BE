from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContentEntity(Base):
    __tablename__ = "mks_lms_content"

    file_id: Mapped[int] = mapped_column("fileId", Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str | None] = mapped_column("fileName", String(500), nullable=True)
    file_description: Mapped[str | None] = mapped_column("fileDescription", String(1000), nullable=True)
    file_path: Mapped[str | None] = mapped_column("fileUrl", String(2000), nullable=True)
    department_id: Mapped[int | None] = mapped_column("department", Integer, nullable=True)
    account_id: Mapped[int | None] = mapped_column("account", Integer, nullable=True)
    category_id: Mapped[int | None] = mapped_column("category", Integer, nullable=True)
    sub_category_id: Mapped[int | None] = mapped_column("subCategory", Integer, nullable=True)
    date_time: Mapped[datetime | None] = mapped_column("createdTIMESTAMP", DateTime, nullable=True)
    user_type: Mapped[int | None] = mapped_column("userType", Integer, nullable=True)
