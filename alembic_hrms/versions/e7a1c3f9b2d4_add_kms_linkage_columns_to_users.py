"""add kms_department_id/kms_account_id/kms_user_type_id to users

Revision ID: e7a1c3f9b2d4
Revises: d4f8c2a6b9e1
Create Date: 2026-08-05 00:00:00.000000

Another instance of the same migration-history gap fixed by c9e2b7a4f1d3 for the
training/certificate tables: UserEntity (app/hrms/models/user.py) declares
kms_department_id/kms_account_id/kms_user_type_id, and its docstring notes these were
added directly via SQL on the live database rather than through a migration, so
0001_initial_schema.py's `users` table never included them. Guarded with a column-
existence check so it's a no-op on databases where they already exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e7a1c3f9b2d4'
down_revision: Union[str, None] = 'd4f8c2a6b9e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ["kms_department_id", "kms_account_id", "kms_user_type_id"]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("users")}

    for column in COLUMNS:
        if column not in existing:
            op.add_column("users", sa.Column(column, sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("users")}

    for column in COLUMNS:
        if column in existing:
            op.drop_column("users", column)
