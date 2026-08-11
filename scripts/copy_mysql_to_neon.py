"""Copies all data from the local MySQL HRMS_DEV_LIVE_DATA database to the Neon Postgres
Dev_HRMS database, for both the KMS (app.models) and HRMS (app.hrms.models) table sets.

Source/target URLs are hardcoded rather than read from settings/.env deliberately: the
app's .env currently has HRMS_DATABASE_URL/DATABASE_URL pointed AT Neon (for some other
purpose), so relying on hrms_settings/settings here would silently make Neon both the
"source" and "target". Local MySQL is unambiguously the source, Neon the target, per the
explicit request this script was written for.

Approach: reuse the SAME SQLAlchemy declarative metadata (Base for KMS, HrmsBase for HRMS)
against both engines - read rows via `select(table)` on the MySQL engine, insert via
`insert(table)` on the Postgres engine. Because both DBs were built from the same models,
this sidesteps all the manual column-name/type-literal handling the earlier dump-import
scripts needed: SQLAlchemy's type system converts MySQL's TINYINT(1)/DATETIME to Python
bool/datetime on read and re-serializes them correctly for Postgres on write.

FK constraints are dropped before loading and re-added (as NOT VALID) afterward, rather
than inserting in dependency order or disabling triggers, for two confirmed reasons:
  - users.reviewed_by is self-referencing - a table can't be topologically sorted before
    itself, so no insertion order avoids a forward reference within the same table.
  - MySQL's `SET FOREIGN_KEY_CHECKS=0` (used when this data was originally bulk-loaded
    into local MySQL earlier this session) let a few genuinely orphaned rows through:
    46 `skills.user_id` rows and 109 `sub_skills.skill_id` rows reference ids that don't
    exist in `users`/`skills` on the source itself. Postgres enforces FK constraints on
    every insert with no equivalent session-level bypass available to a non-superuser
    role (`ALTER TABLE ... DISABLE TRIGGER` fails on Neon: "is a system trigger"), so
    dropping the constraint is the only way to load the data faithfully as it already
    exists on local rather than silently dropping or rewriting those rows.
NOT VALID means the constraint applies to future inserts/updates (matching local's schema
intent) without retroactively validating the rows just loaded (matching local's actual,
imperfect data).

Neon's data tables are truncated first (per explicit confirmation - Neon had a handful of
leftover bootstrap/test rows whose ids and unique emails collide with local's real data),
using TRUNCATE ... RESTART IDENTITY CASCADE so sequence resets are handled by Postgres
itself. Tables that exist only on Neon (legacy reflected tables like `migrations`,
`failed_jobs` - never part of either app model, no equivalent in local MySQL) are left
untouched, and so are their FK constraints (none reference tables in scope here).
"""
import asyncio

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.hrms.models import HrmsBase
from app.models import Base

MYSQL_URL = "mysql+asyncmy://root:@localhost:3306/HRMS_DEV_LIVE_DATA"
NEON_URL = "postgresql+asyncpg://neondb_owner:npg_lWPTCkQixK61@ep-mute-bonus-azco7c1l-pooler.c-3.ap-southeast-1.aws.neon.tech/Dev_HRMS"

CHUNK_SIZE = 500


async def get_fk_constraints(target_engine, table_names):
    async with target_engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT conname, conrelid::regclass::text AS table_name, pg_get_constraintdef(oid) AS def
                FROM pg_constraint
                WHERE contype = 'f' AND connamespace = 'public'::regnamespace
                  AND conrelid::regclass::text = ANY(:names)
                """
            ),
            {"names": list(table_names)},
        )
        return [dict(row._mapping) for row in result]


async def drop_constraints(target_engine, constraints):
    async with target_engine.begin() as conn:
        for c in constraints:
            await conn.exec_driver_sql(f'ALTER TABLE "{c["table_name"]}" DROP CONSTRAINT "{c["conname"]}"')


async def restore_constraints(target_engine, constraints):
    async with target_engine.begin() as conn:
        for c in constraints:
            await conn.exec_driver_sql(
                f'ALTER TABLE "{c["table_name"]}" ADD CONSTRAINT "{c["conname"]}" {c["def"]} NOT VALID'
            )


async def truncate_all(target_engine, tables):
    names = ", ".join(f'"{t.name}"' for t in tables)
    async with target_engine.begin() as conn:
        await conn.exec_driver_sql(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE")


async def copy_table(source_engine, target_engine, table):
    async with source_engine.connect() as conn:
        result = await conn.execute(select(table))
        rows = [dict(row._mapping) for row in result]

    if not rows:
        return 0

    async with target_engine.begin() as conn:
        for i in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[i : i + CHUNK_SIZE]
            await conn.execute(insert(table), chunk)

        for col in table.primary_key.columns:
            try:
                if col.type.python_type is not int:
                    continue
            except NotImplementedError:
                continue
            try:
                await conn.exec_driver_sql(
                    f"SELECT setval(pg_get_serial_sequence('\"{table.name}\"', '{col.name}'), "
                    f"(SELECT COALESCE(MAX(\"{col.name}\"), 1) FROM \"{table.name}\"), "
                    f"(SELECT MAX(\"{col.name}\") IS NOT NULL FROM \"{table.name}\"))"
                )
            except Exception:
                pass  # not every integer PK is backed by a sequence

    return len(rows)


async def main():
    source_engine = create_async_engine(MYSQL_URL)
    target_engine = create_async_engine(NEON_URL, connect_args={"ssl": "require"})

    kms_tables = list(Base.metadata.sorted_tables)
    hrms_tables = list(HrmsBase.metadata.sorted_tables)
    all_tables = kms_tables + hrms_tables
    table_names = [t.name for t in all_tables]

    constraints = await get_fk_constraints(target_engine, table_names)
    print(f"Dropping {len(constraints)} FK constraints on Neon...")
    await drop_constraints(target_engine, constraints)

    print(f"Truncating {len(all_tables)} tables on Neon...")
    await truncate_all(target_engine, all_tables)

    print("\n--- Copying KMS tables ---")
    for table in kms_tables:
        n = await copy_table(source_engine, target_engine, table)
        print(f"  {table.name}: {n} rows")

    print("\n--- Copying HRMS tables ---")
    for table in hrms_tables:
        n = await copy_table(source_engine, target_engine, table)
        print(f"  {table.name}: {n} rows")

    print(f"\nRestoring {len(constraints)} FK constraints (NOT VALID)...")
    await restore_constraints(target_engine, constraints)

    await source_engine.dispose()
    await target_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
