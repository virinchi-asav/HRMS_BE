"""One-off data migration: load INSERT rows from D:/HRMS/KMSDump20260806.sql (a dump of
the legacy Java/Hibernate KMS backend) into the currently-configured KMS database, and
cross-link the loaded KMS user data into the unified HRMS `users` table.

CREATE/ALTER statements in the dump are ignored - only INSERT INTO ... VALUES statements
are used. Unlike old_hrms_data.sql, these INSERT statements have NO explicit column list
(`INSERT INTO t VALUES (...)`), so each table's column order is supplied here from the
dump's own CREATE TABLE statements (read for that purpose only, never executed).

Two schema-drift cases are handled explicitly, both confirmed against the live target
schema before writing this:
  - mks_lms_content: the dump's `createdDateTime` column is `createdTIMESTAMP` in this
    app's schema (same data, renamed at some point after the dump was taken).
  - BIT(1) columns (mks_kms_category.unrestrictedCategory, mks_kms_usermgmt.enabled/
    password_reset_required) are TINYINT(1) here. MySQL strict mode refuses to coerce a
    `_binary '\\x01'`-style bit literal into an integer column (confirmed empirically -
    it raises 1366, it does not silently corrupt), so those three columns are decoded to
    a plain 0/1 integer literal before the INSERT is built.

`hibernate_sequence` (Hibernate's internal PK-sequence counter) has no equivalent table
in this schema and is skipped - nothing in this codebase reads it.

After the direct per-table loads, `mks_kms_usermgmt` + `user_account` + `user_department`
+ `users_type` (the old KMS-only login/scoping tables) are joined by `user_email` against
`users.email` to backfill `users.kms_account_id/kms_department_id/kms_user_type_id` -
the same "single-login unification" fields described in app/hrms/models/user.py. This is
matched by email, not by user_id, since the old KMS Hibernate `user_id` sequence and the
HRMS `users.id` sequence are two unrelated ID spaces.

FOREIGN_KEY_CHECKS is disabled for the load and INSERT IGNORE is used, matching
import_old_hrms_data.py's approach, so this is safe to re-run.
"""
import asyncio
import warnings

import sqlglot
from sqlglot import exp
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

DUMP_PATH = "D:/HRMS/KMSDump20260806.sql"

# The dump's INSERT statements have no column list - order taken from the dump's own
# CREATE TABLE statements (not executed, just read for this).
COLUMN_ORDER = {
    "hibernate_sequence": ["next_val"],
    "mks_kms_account": ["accountId", "accountDescription", "accountName", "departmentId"],
    "mks_kms_category": ["categoryId", "categoryDescription", "categoryName", "unrestrictedCategory"],
    "mks_kms_department": ["departmentId", "departmentDescription", "departmentName"],
    "mks_kms_subcategory": ["subCategoryId", "subCategoryDescription", "subCategoryName"],
    "mks_kms_usermgmt": [
        "user_id", "user_created_ts", "user_email", "enabled", "user_last_logged_in_ts",
        "user_pwd", "password_reset_required", "user_updated_ts", "user_name",
        "password_reset_token", "token_created_time", "profile_image_url",
    ],
    "mks_lms_content": [
        "fileId", "account", "category", "createdDateTime", "department", "fileDescription",
        "fileName", "fileUrl", "userType", "subCategory",
    ],
    "mks_lms_roles": ["role_id", "role_name"],
    "mks_lms_user_type": ["user_type_id", "user_type_name"],
    "user_account": ["accountId", "user_id"],
    "user_department": ["departmentId", "user_id"],
    "users_roles": ["role_id", "user_id"],
    "users_type": ["user_type_id", "user_id"],
}

RENAME_MAP = {
    "mks_lms_content": {"createdDateTime": "createdTIMESTAMP"},
}

# (table, column) -> decode the dump's BIT(1) literal to a plain 0/1 int literal, since
# the target column is TINYINT(1) and strict mode rejects the raw binary-string literal.
BIT_COLUMNS = {
    ("mks_kms_category", "unrestrictedCategory"),
    ("mks_kms_usermgmt", "enabled"),
    ("mks_kms_usermgmt", "password_reset_required"),
}

MYSQL_ESCAPES = {
    "0": "\x00", "'": "'", '"': '"', "b": "\x08", "n": "\n", "r": "\r",
    "t": "\t", "Z": "\x1a", "\\": "\\",
}


def mysql_unescape(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append(MYSQL_ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def bit_literal_to_sql(value_node) -> str:
    if isinstance(value_node, exp.Null) or value_node is None:
        return "NULL"
    raw = value_node.expression.this if isinstance(value_node, exp.Introducer) else value_node.this
    decoded = mysql_unescape(raw)
    return "1" if decoded and ord(decoded[-1]) & 1 else "0"


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


async def load_tables(engine, table_columns):
    with open(DUMP_PATH, encoding="utf-8", errors="replace") as f:
        text = f.read()

    statements = sqlglot.parse(text, dialect="mysql", error_level=sqlglot.ErrorLevel.IGNORE)
    inserts = [s for s in statements if isinstance(s, exp.Insert)]
    print(f"Parsed {len(inserts)} INSERT statements from dump")

    touched_tables = {ins.this.name if isinstance(ins.this, exp.Table) else ins.this.this.name for ins in inserts}

    async with engine.begin() as conn:
        before = await get_row_counts(conn, [t for t in touched_tables if t in table_columns])

        await conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        try:
            skipped_tables = set()
            for ins in inserts:
                table = ins.this.name if isinstance(ins.this, exp.Table) else ins.this.this.name

                if table not in table_columns:
                    skipped_tables.add(table)
                    continue
                if table not in COLUMN_ORDER:
                    raise RuntimeError(f"No known column order for table {table!r} - add it to COLUMN_ORDER")

                source_cols = COLUMN_ORDER[table]
                renames = RENAME_MAP.get(table, {})
                mapped_cols = [renames.get(c, c) for c in source_cols]
                target_cols = set(table_columns[table])
                bit_positions = {i for i, c in enumerate(source_cols) if (table, c) in BIT_COLUMNS}

                keep_idx = [i for i, c in enumerate(mapped_cols) if c in target_cols]
                kept_cols = [mapped_cols[i] for i in keep_idx]
                if not kept_cols:
                    continue

                rows = ins.expression.expressions
                col_list_sql = ", ".join(f"`{c}`" for c in kept_cols)
                row_sqls = []
                for row in rows:
                    vals = row.expressions
                    kept_vals_sql = [
                        bit_literal_to_sql(vals[i]) if i in bit_positions else vals[i].sql(dialect="mysql")
                        for i in keep_idx
                    ]
                    row_sqls.append(f"({', '.join(kept_vals_sql)})")

                sql_text = f"INSERT IGNORE INTO `{table}` ({col_list_sql}) VALUES {', '.join(row_sqls)}"
                await conn.exec_driver_sql(sql_text.replace("%", "%%"))
        finally:
            await conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")

        after = await get_row_counts(conn, [t for t in touched_tables if t in table_columns])

    print("\n--- Direct table load results ---")
    for t in sorted(touched_tables):
        if t not in table_columns:
            print(f"{t}: SKIPPED (no such table in current schema)")
            continue
        print(f"{t}: {before[t]} -> {after[t]} (+{after[t] - before[t]})")


async def backfill_hrms_users(engine):
    """Cross-link KMS user scoping into the unified `users` table, matched by email."""
    async with engine.begin() as conn:
        result = await conn.exec_driver_sql(
            """
            UPDATE users u
            JOIN mks_kms_usermgmt k ON k.user_email = u.email
            LEFT JOIN user_account ua ON ua.user_id = k.user_id
            LEFT JOIN user_department ud ON ud.user_id = k.user_id
            LEFT JOIN users_type ut ON ut.user_id = k.user_id
            SET
                u.kms_account_id = COALESCE(ua.accountId, u.kms_account_id),
                u.kms_department_id = COALESCE(ud.departmentId, u.kms_department_id),
                u.kms_user_type_id = COALESCE(ut.user_type_id, u.kms_user_type_id)
            """
        )
        print(f"\n--- users backfill ---\nusers rows updated: {result.rowcount}")

        unmatched = await conn.exec_driver_sql(
            "SELECT COUNT(*) FROM mks_kms_usermgmt k "
            "WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.email = k.user_email)"
        )
        print(f"mks_kms_usermgmt rows with no matching users.email: {unmatched.scalar()}")


async def main():
    warnings.filterwarnings("ignore", message=".*Duplicate entry.*")
    engine = create_async_engine(settings.sqlalchemy_database_uri)
    print("Target:", settings.sqlalchemy_database_uri)

    table_columns = await get_table_columns(engine)
    await load_tables(engine, table_columns)
    await backfill_hrms_users(engine)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
