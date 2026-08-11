"""backfill missing training and certificate tables

Revision ID: c9e2b7a4f1d3
Revises: b14399f5a21f
Create Date: 2026-08-06 10:00:00.000000

This closes a gap in the migration history, not a new feature: training_programs,
training_trainees, training_day_entries, training_comments, training_materials,
training_assessments, training_assessment_screenshots, certificate_templates, and
training_certificates have existed on the live MySQL database (and now on the Neon
Postgres copy) since early development, but were bootstrapped there directly from
HrmsBase.metadata.create_all() rather than a tracked migration - no revision in this
history ever actually creates them.

Inserted right after b14399f5a21f (not appended at the current head) because
ac6ecc4a9c28, immediately downstream in the original chain, already ALTERs
training_programs and task_assessment_tasks assuming training_programs exists - on a
genuinely fresh database that ALTER fails otherwise. ac6ecc4a9c28's down_revision is
updated to point here instead of directly to b14399f5a21f, so the effective head
revision id (f3c7a9d1e8b2) is unchanged - already-migrated databases (MySQL, Neon) stay
exactly where they are and treat `upgrade head` as a no-op, while a brand new database
now walks this table-creation step at the correct point in the sequence.

Confirmed via a column-by-column diff against the live MySQL database before writing
this: every column below matches the current models exactly (with the single deliberate
exception of training_programs.assessment_given_by, noted below, which belongs to the
next migration in sequence) - this is a pure backfill of the missing CREATE statements,
not a schema change.

Every create is guarded by a has_table() check so this is a safe no-op on any database
that (like the existing MySQL dev DB, or a Neon copy seeded via create_all) already has
these tables, while still correctly building them from scratch on a genuinely new
database that only ever goes through `alembic upgrade head`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9e2b7a4f1d3'
down_revision: Union[str, None] = 'b14399f5a21f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), 'sqlite')


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'training_programs' not in existing_tables:
        op.create_table(
            'training_programs',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('topic', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('account_id', sa.Integer(), nullable=True),
            sa.Column('trainer_id', sa.BigInteger(), nullable=False),
            sa.Column('bu_head_id', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=False),
            sa.Column('has_assessment', sa.Boolean(), nullable=False),
            # assessment_given_by is intentionally NOT created here - it's added by the
            # very next migration, ac6ecc4a9c28, which is where it belongs historically.
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('created_by', sa.BigInteger(), nullable=False),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('rejected_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['trainer_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['bu_head_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'training_trainees' not in existing_tables:
        op.create_table(
            'training_trainees',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('training_id', sa.BigInteger(), nullable=False),
            sa.Column('trainee_id', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(['training_id'], ['training_programs.id'], ),
            sa.ForeignKeyConstraint(['trainee_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('training_id', 'trainee_id', name='uq_training_trainee'),
        )

    if 'training_day_entries' not in existing_tables:
        op.create_table(
            'training_day_entries',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('training_id', sa.BigInteger(), nullable=False),
            sa.Column('entry_date', sa.Date(), nullable=False),
            sa.Column('topic_covered', sa.String(length=500), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=False),
            sa.Column('created_by', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['training_id'], ['training_programs.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'training_comments' not in existing_tables:
        op.create_table(
            'training_comments',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('training_id', sa.BigInteger(), nullable=False),
            sa.Column('author_id', sa.BigInteger(), nullable=False),
            sa.Column('comment', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['training_id'], ['training_programs.id'], ),
            sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'training_materials' not in existing_tables:
        op.create_table(
            'training_materials',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('training_id', sa.BigInteger(), nullable=False),
            sa.Column('material_type', sa.String(length=20), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('link_url', sa.String(length=2000), nullable=True),
            sa.Column('file_path', sa.String(length=500), nullable=True),
            sa.Column('added_by', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['training_id'], ['training_programs.id'], ),
            sa.ForeignKeyConstraint(['added_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'training_assessments' not in existing_tables:
        op.create_table(
            'training_assessments',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('training_id', sa.BigInteger(), nullable=False),
            sa.Column('trainee_id', sa.BigInteger(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('detail_document_path', sa.String(length=500), nullable=True),
            sa.Column('status', sa.String(length=30), nullable=False),
            sa.Column('github_repo_url', sa.String(length=2000), nullable=True),
            sa.Column('project_zip_path', sa.String(length=500), nullable=True),
            sa.Column('marks', sa.Integer(), nullable=True),
            sa.Column('reviewed_by', sa.BigInteger(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['training_id'], ['training_programs.id'], ),
            sa.ForeignKeyConstraint(['trainee_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('training_id', 'trainee_id', name='uq_training_assessment_trainee'),
        )

    if 'training_assessment_screenshots' not in existing_tables:
        op.create_table(
            'training_assessment_screenshots',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('assessment_id', sa.BigInteger(), nullable=False),
            sa.Column('file_path', sa.String(length=500), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['assessment_id'], ['training_assessments.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'certificate_templates' not in existing_tables:
        op.create_table(
            'certificate_templates',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('file_path', sa.String(length=500), nullable=False),
            sa.Column('uploaded_by', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'training_certificates' not in existing_tables:
        op.create_table(
            'training_certificates',
            sa.Column('id', BIGINT, nullable=False),
            sa.Column('training_id', sa.BigInteger(), nullable=False),
            sa.Column('trainee_id', sa.BigInteger(), nullable=False),
            sa.Column('recipient_name', sa.String(length=255), nullable=False),
            sa.Column('topic', sa.String(length=255), nullable=False),
            sa.Column('issue_date', sa.Date(), nullable=False),
            sa.Column('generated_file_path', sa.String(length=500), nullable=False),
            sa.Column('issued_by', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['training_id'], ['training_programs.id'], ),
            sa.ForeignKeyConstraint(['trainee_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('training_id', 'trainee_id', name='uq_training_certificate_trainee'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Reverse dependency order.
    for table in (
        'training_certificates',
        'certificate_templates',
        'training_assessment_screenshots',
        'training_assessments',
        'training_materials',
        'training_comments',
        'training_day_entries',
        'training_trainees',
        'training_programs',
    ):
        if table in existing_tables:
            op.drop_table(table)
