import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ALEMBIC_DATABASE_URL_KMS lets a one-off `alembic -c alembic.ini upgrade` target a
# different database without touching settings/.env, which stays pointed at this app's
# normal database. Leave unset for normal use. (Distinct from alembic_hrms's
# ALEMBIC_DATABASE_URL - the two chains are independent and may need different targets
# when testing.)
_database_url = os.environ.get("ALEMBIC_DATABASE_URL_KMS") or settings.sqlalchemy_database_uri
config.set_main_option("sqlalchemy.url", _database_url)

target_metadata = Base.metadata

# This chain and alembic_hrms's chain are two independent migration histories that
# happen to target the same physical database in this dev setup - each MUST use its own
# version-tracking table (rather than the default shared "alembic_version") or one
# chain's stamped revision looks like nonsense to the other's environment, since neither
# recognizes the other's revision ids. See alembic_hrms/env.py for the matching setting.
VERSION_TABLE = "alembic_version_kms"


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
