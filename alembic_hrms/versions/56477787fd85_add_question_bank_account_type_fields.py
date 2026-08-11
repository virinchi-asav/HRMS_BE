"""add question bank account type fields

Revision ID: 56477787fd85
Revises: ac6ecc4a9c28
Create Date: 2026-07-27 19:00:55.009494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '56477787fd85'
down_revision: Union[str, None] = 'ac6ecc4a9c28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hand-pruned from the raw autogenerate output, which also picked up the same
    # pre-existing drift as prior migrations (unrelated KMS/legacy tables and type-only
    # diffs) - only the 2 new columns for this feature are applied here.
    op.add_column('task_question_banks', sa.Column('account_id', sa.Integer(), nullable=True))
    op.add_column('task_question_banks', sa.Column('custom_account_type', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('task_question_banks', 'custom_account_type')
    op.drop_column('task_question_banks', 'account_id')
