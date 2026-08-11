"""One-off data migration: load INSERT rows from D:/HRMS/old_hrms_data.sql (a mysqldump
of the legacy live database) into the currently-configured HRMS database.

CREATE/ALTER statements in the dump are ignored - only INSERT INTO ... VALUES statements
are used, and only for tables that actually exist in the current schema (e.g. `migrations`
has no model/table here and is skipped). Column lists are intersected with the target
table's real columns, so this tolerates schema drift both ways: columns the current
schema added since the dump was taken (e.g. users.kms_department_id) are simply left at
their default/NULL, and any dump columns no longer present are dropped positionally
along with their matching value.

FOREIGN_KEY_CHECKS is disabled for the load (dump order isn't topologically sorted -
e.g. users.reviewed_by is self-referential) and re-enabled afterwards. INSERT IGNORE is
used so the script is safe to re-run without duplicating rows or aborting on a stray
primary-key collision.
"""
import asyncio
import warnings

import sqlglot
from sqlglot import exp
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.hrms.core.config import hrms_settings

DUMP_PATH = "D:/HRMS/old_hrms_data.sql"


async def get_table_columns(engine):
    async with engine.connect() as conn:
        def _inspect(sync_conn):
            insp = sa_inspect(sync_conn)
            return {t: [c["name"] for c in insp.get_columns(t)] for t in insp.get_table_names()}

        return await conn.run_sync(_inspect)


async def get_row_counts(conn, tables):
    counts = {}
    for t in tables:
        result = await conn.exec_driver_sql(f"SELECT COUNT(*) FROM `{t}`")
        counts[t] = result.scalar()
    return counts


async def main():
    warnings.filterwarnings("ignore", message=".*Duplicate entry.*")
    engine = create_async_engine(hrms_settings.sqlalchemy_database_uri)
    print("Target:", hrms_settings.sqlalchemy_database_uri)

    table_columns = await get_table_columns(engine)

    with open(DUMP_PATH, encoding="utf-8", errors="replace") as f:
        text = f.read()

    statements = sqlglot.parse(text, dialect="mysql", error_level=sqlglot.ErrorLevel.IGNORE)
    inserts = [s for s in statements if isinstance(s, exp.Insert)]
    print(f"Parsed {len(inserts)} INSERT statements from dump")

    touched_tables = set()
    for ins in inserts:
        schema = ins.this
        table = schema.this.name if isinstance(schema, exp.Schema) else schema.name
        touched_tables.add(table)

    async with engine.begin() as conn:
        before = await get_row_counts(conn, [t for t in touched_tables if t in table_columns])

        await conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        try:
            skipped_tables = set()
            dropped_columns_by_table = {}

            for ins in inserts:
                schema = ins.this
                table = schema.this.name if isinstance(schema, exp.Schema) else schema.name

                if table not in table_columns:
                    skipped_tables.add(table)
                    continue

                target_cols = set(table_columns[table])
                col_idents = schema.expressions if isinstance(schema, exp.Schema) else []
                col_names = [c.name for c in col_idents]
                keep_idx = [i for i, c in enumerate(col_names) if c in target_cols]
                dropped = [c for c in col_names if c not in target_cols]
                if dropped:
                    dropped_columns_by_table[table] = sorted(set(dropped))
                kept_cols = [col_names[i] for i in keep_idx]
                if not kept_cols:
                    continue

                rows = ins.expression.expressions
                col_list_sql = ", ".join(f"`{c}`" for c in kept_cols)
                row_sqls = []
                for row in rows:
                    vals = row.expressions
                    kept_vals_sql = [vals[i].sql(dialect="mysql") for i in keep_idx]
                    row_sqls.append(f"({', '.join(kept_vals_sql)})")

                sql_text = f"INSERT IGNORE INTO `{table}` ({col_list_sql}) VALUES {', '.join(row_sqls)}"
                # asyncmy's cursor.execute() runs `query % args` even with no bound params,
                # so a literal `%` in any string value (dates, notes, emails with %-encoding,
                # etc.) must be escaped as `%%` or it's misread as a format placeholder.
                await conn.exec_driver_sql(sql_text.replace("%", "%%"))
        finally:
            await conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")

        after = await get_row_counts(conn, [t for t in touched_tables if t in table_columns])

    await engine.dispose()

    print("\n--- Results ---")
    for t in sorted(touched_tables):
        if t not in table_columns:
            print(f"{t}: SKIPPED (no such table in current schema)")
            continue
        added = after[t] - before[t]
        note = f"  (dropped columns not in current schema: {dropped_columns_by_table[t]})" if t in dropped_columns_by_table else ""
        print(f"{t}: {before[t]} -> {after[t]} (+{added}){note}")


if __name__ == "__main__":
    asyncio.run(main())
