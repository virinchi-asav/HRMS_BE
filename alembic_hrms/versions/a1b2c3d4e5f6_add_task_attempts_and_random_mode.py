"""add task attempts and random question mode

Revision ID: a1b2c3d4e5f6
Revises: d3f8a1c9b6e2
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd3f8a1c9b6e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('task_assessment_tasks', sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'))
    op.add_column(
        'task_assessment_tasks',
        sa.Column('question_mode', sa.String(length=20), nullable=False, server_default='MANUAL'),
    )
    op.add_column('task_assessment_tasks', sa.Column('source_bank_id', sa.BigInteger(), nullable=True))
    op.add_column('task_assessment_tasks', sa.Column('source_module_name', sa.String(length=255), nullable=True))
    op.add_column('task_assessment_tasks', sa.Column('random_question_count', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_task_assessment_tasks_source_bank_id',
        'task_assessment_tasks', 'task_question_banks',
        ['source_bank_id'], ['id'],
    )

    op.add_column(
        'task_assessment_assignees', sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1')
    )
    op.add_column('task_assessment_assignees', sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('task_assessment_assignees', sa.Column('submit_reason', sa.String(length=20), nullable=True))
    # Create the new constraint before dropping the old one - task_assessment_assignees
    # has an outgoing FK on task_id, and MySQL/InnoDB refuses to drop whichever index
    # currently backs that FK unless another index covering task_id already exists.
    # Both uq_task_assignee_trainee(task_id, trainee_id) and its replacement
    # (task_id, trainee_id, attempt_number) lead with task_id, so creating the
    # replacement first keeps an eligible index in place the whole time.
    op.create_unique_constraint(
        'uq_task_assignee_trainee_attempt',
        'task_assessment_assignees',
        ['task_id', 'trainee_id', 'attempt_number'],
    )
    op.drop_constraint('uq_task_assignee_trainee', 'task_assessment_assignees', type_='unique')

    op.add_column('task_assessment_task_questions', sa.Column('assignee_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_task_assessment_task_questions_assignee_id',
        'task_assessment_task_questions', 'task_assessment_assignees',
        ['assignee_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_task_assessment_task_questions_assignee_id', 'task_assessment_task_questions', type_='foreignkey')
    op.drop_column('task_assessment_task_questions', 'assignee_id')

    op.create_unique_constraint('uq_task_assignee_trainee', 'task_assessment_assignees', ['task_id', 'trainee_id'])
    op.drop_constraint('uq_task_assignee_trainee_attempt', 'task_assessment_assignees', type_='unique')
    op.drop_column('task_assessment_assignees', 'submit_reason')
    op.drop_column('task_assessment_assignees', 'max_attempts')
    op.drop_column('task_assessment_assignees', 'attempt_number')

    op.drop_constraint('fk_task_assessment_tasks_source_bank_id', 'task_assessment_tasks', type_='foreignkey')
    op.drop_column('task_assessment_tasks', 'random_question_count')
    op.drop_column('task_assessment_tasks', 'source_module_name')
    op.drop_column('task_assessment_tasks', 'source_bank_id')
    op.drop_column('task_assessment_tasks', 'question_mode')
    op.drop_column('task_assessment_tasks', 'max_attempts')
