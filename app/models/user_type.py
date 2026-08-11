from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserTypeEntity(Base):
    __tablename__ = "mks_lms_user_type"

    id: Mapped[int] = mapped_column("user_type_id", Integer, primary_key=True, autoincrement=True)
    type_name: Mapped[str] = mapped_column("user_type_name", String(255), nullable=False, unique=True)
