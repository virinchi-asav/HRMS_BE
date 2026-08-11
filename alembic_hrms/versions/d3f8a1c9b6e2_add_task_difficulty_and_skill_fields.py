"""add task difficulty and skill fields

Revision ID: d3f8a1c9b6e2
Revises: 56477787fd85
Create Date: 2026-08-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3f8a1c9b6e2'
down_revision: Union[str, None] = '56477787fd85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('task_assessment_tasks', sa.Column('difficulty_level', sa.String(length=20), nullable=True))
    op.add_column('task_assessment_tasks', sa.Column('skill_name', sa.String(length=255), nullable=True))
    op.add_column('task_assessment_tasks', sa.Column('skill_category', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('task_assessment_tasks', 'skill_category')
    op.drop_column('task_assessment_tasks', 'skill_name')
    op.drop_column('task_assessment_tasks', 'difficulty_level')
