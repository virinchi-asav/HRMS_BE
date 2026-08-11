"""widen integer FKs to bigint and add the missing constraints

Revision ID: d4f8c2a6b9e1
Revises: f3c7a9d1e8b2
Create Date: 2026-08-06 11:00:00.000000

Brings already-existing databases in line with the fix made to 0001_initial_schema.py's
candidates.job_id/clientsurvey.customer_id/skills.user_id columns (Integer -> BigInteger,
to match the BigInteger primary key each one references). Two situations, both handled:

- MySQL: these columns were plain Integer with NO foreign key at all (Laravel never
  declared one at the DB level - see 0001's docstring). Widening is a safe, backwards-
  compatible column change; the FK is then added fresh. Checked beforehand for orphaned
  rows that would violate it - there were none.
- Postgres (Neon): create_all() already added the FK despite the type mismatch (Postgres
  tolerates the implicit widening cast that MySQL 8 rejects), but the column itself was
  never widened. Only the column type change applies here; the FK-existence check below
  skips the already-present constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4f8c2a6b9e1'
down_revision: Union[str, None] = 'f3c7a9d1e8b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, referenced_table)
FIXES = [
    ('candidates', 'job_id', 'jobs'),
    ('clientsurvey', 'customer_id', 'clients'),
    ('skills', 'user_id', 'users'),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table, column, _ in FIXES:
        op.alter_column(table, column, existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)

    for table, column, referenced_table in FIXES:
        has_fk = any(fk['constrained_columns'] == [column] for fk in inspector.get_foreign_keys(table))
        if not has_fk:
            op.create_foreign_key(
                f'fk_{table}_{column}', table, referenced_table, [column], ['id']
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table, column, referenced_table in FIXES:
        for fk in inspector.get_foreign_keys(table):
            if fk['constrained_columns'] == [column]:
                op.drop_constraint(fk['name'], table, type_='foreignkey')

    for table, column, _ in FIXES:
        op.alter_column(table, column, existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
