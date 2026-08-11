"""add task assessment tables

Revision ID: b14399f5a21f
Revises: 0001
Create Date: 2026-07-27 11:13:27.997626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b14399f5a21f'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hand-pruned from the raw autogenerate output, which also picked up a large amount
    # of pre-existing drift unrelated to this feature (KMS module tables that live on a
    # separate declarative Base/metadata sharing this physical DB, legacy Laravel
    # tables, and type-only diffs on unrelated columns) - only the 8 new tables for this
    # feature are created here.
    op.create_table('task_assessment_tasks',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('time_limit_minutes', sa.Integer(), nullable=False),
    sa.Column('pass_percentage', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_question_banks',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_assessment_assignees',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('task_id', sa.BigInteger(), nullable=False),
    sa.Column('trainee_id', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('deadline_at', sa.DateTime(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('marks_obtained', sa.Integer(), nullable=True),
    sa.Column('total_marks', sa.Integer(), nullable=True),
    sa.Column('percentage', sa.Float(), nullable=True),
    sa.Column('passed', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['task_id'], ['task_assessment_tasks.id'], ),
    sa.ForeignKeyConstraint(['trainee_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id', 'trainee_id', name='uq_task_assignee_trainee')
    )
    op.create_table('task_question_bank_questions',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('bank_id', sa.BigInteger(), nullable=False),
    sa.Column('module_name', sa.String(length=255), nullable=False),
    sa.Column('question_type', sa.String(length=20), nullable=False),
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('marks', sa.Integer(), nullable=False),
    sa.Column('correct_answer_text', sa.String(length=500), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['bank_id'], ['task_question_banks.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_assessment_task_questions',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('task_id', sa.BigInteger(), nullable=False),
    sa.Column('source_question_id', sa.BigInteger(), nullable=True),
    sa.Column('module_name', sa.String(length=255), nullable=True),
    sa.Column('question_type', sa.String(length=20), nullable=False),
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('correct_answer_text', sa.String(length=500), nullable=True),
    sa.Column('marks', sa.Integer(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['source_question_id'], ['task_question_bank_questions.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['task_assessment_tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_question_bank_question_options',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('question_id', sa.BigInteger(), nullable=False),
    sa.Column('option_text', sa.String(length=500), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['task_question_bank_questions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_assessment_task_question_options',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('task_question_id', sa.BigInteger(), nullable=False),
    sa.Column('option_text', sa.String(length=500), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['task_question_id'], ['task_assessment_task_questions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_assessment_answers',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('assignee_id', sa.BigInteger(), nullable=False),
    sa.Column('task_question_id', sa.BigInteger(), nullable=False),
    sa.Column('selected_option_id', sa.BigInteger(), nullable=True),
    sa.Column('answer_text', sa.Text(), nullable=True),
    sa.Column('is_correct', sa.Boolean(), nullable=True),
    sa.Column('marks_awarded', sa.Integer(), nullable=True),
    sa.Column('answered_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assignee_id'], ['task_assessment_assignees.id'], ),
    sa.ForeignKeyConstraint(['selected_option_id'], ['task_assessment_task_question_options.id'], ),
    sa.ForeignKeyConstraint(['task_question_id'], ['task_assessment_task_questions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('assignee_id', 'task_question_id', name='uq_task_answer_assignee_question')
    )


def downgrade() -> None:
    op.drop_table('task_assessment_answers')
    op.drop_table('task_assessment_task_question_options')
    op.drop_table('task_question_bank_question_options')
    op.drop_table('task_assessment_task_questions')
    op.drop_table('task_question_bank_questions')
    op.drop_table('task_assessment_assignees')
    op.drop_table('task_question_banks')
    op.drop_table('task_assessment_tasks')
