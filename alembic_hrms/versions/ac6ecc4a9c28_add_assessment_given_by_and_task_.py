"""add assessment_given_by and task training_id link

Revision ID: ac6ecc4a9c28
Revises: c9e2b7a4f1d3
Create Date: 2026-07-27 12:27:21.599511

Re-pointed from b14399f5a21f to c9e2b7a4f1d3 (which now sits between the two) when the
missing training_programs CREATE was backfilled into history - this migration ALTERs
training_programs and always needed it to exist first, which prior to that backfill was
only true by accident on already-bootstrapped databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ac6ecc4a9c28'
down_revision: Union[str, None] = 'c9e2b7a4f1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hand-pruned from the raw autogenerate output (same pre-existing drift as the prior
    # migration - unrelated KMS/legacy tables and type-only diffs) - only the 2 new
    # columns for this feature are applied here.
    op.add_column('training_programs', sa.Column('assessment_given_by', sa.String(length=20), nullable=True))
    op.add_column('task_assessment_tasks', sa.Column('training_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(None, 'task_assessment_tasks', 'training_programs', ['training_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'task_assessment_tasks', type_='foreignkey')
    op.drop_column('task_assessment_tasks', 'training_id')
    op.drop_column('training_programs', 'assessment_given_by')
