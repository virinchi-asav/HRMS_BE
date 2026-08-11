from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountEntity(Base):
    __tablename__ = "mks_kms_account"

    account_id: Mapped[int] = mapped_column("accountId", Integer, primary_key=True, autoincrement=True)
    account_name: Mapped[str] = mapped_column("accountName", String(255), nullable=False, unique=True)
    account_description: Mapped[str | None] = mapped_column("accountDescription", String(1000), nullable=True)
    department_id: Mapped[int | None] = mapped_column("departmentId", Integer, nullable=True)
