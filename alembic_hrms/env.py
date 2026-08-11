import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.hrms.core.config import hrms_settings
from app.hrms.models import HrmsBase

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ALEMBIC_DATABASE_URL lets a one-off `alembic upgrade` target a different database
# (e.g. a new Postgres/Neon environment) without touching hrms_settings/.env, which
# stays pointed at this app's normal MySQL database. Leave unset for normal use.
_database_url = os.environ.get("ALEMBIC_DATABASE_URL") or hrms_settings.sqlalchemy_database_uri
# set_main_option() goes through configparser's interpolation, which treats "%" as the
# start of a %(name)s reference - escape it as "%%" so a percent-encoded URL (e.g. an
# "@" in the password rendered as "%40") round-trips correctly on get_main_option().
config.set_main_option("sqlalchemy.url", _database_url.replace("%", "%%"))

target_metadata = HrmsBase.metadata

# This chain and the KMS-side alembic/ chain are two independent migration histories
# that happen to target the same physical database in this dev setup - each MUST use
# its own version-tracking table (rather than the default shared "alembic_version") or
# one chain's stamped revision looks like nonsense to the other's environment, since
# neither recognizes the other's revision ids. See alembic/env.py for the matching
# setting on the KMS side.
VERSION_TABLE = "alembic_version_hrms"


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    # Neon (and most managed Postgres) requires TLS; asyncpg wants this passed as a
    # connect arg rather than a "sslmode"-style URL query param (that's libpq syntax,
    # not something asyncpg's connect() understands).
    connect_args = {"ssl": "require"} if url.startswith("postgresql+asyncpg") else {}
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
