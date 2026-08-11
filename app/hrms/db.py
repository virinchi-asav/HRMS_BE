from collections.abc import AsyncGenerator

from sqlalchemy import BigInteger, Integer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.hrms.core.config import hrms_settings

# SQLite's "INTEGER PRIMARY KEY becomes an alias for ROWID and auto-increments" trick
# only fires for a column literally typed INTEGER - BIGINT (what plain BigInteger
# compiles to) doesn't qualify, so PK auto-assignment silently fails under SQLite (used
# for tests). MySQL's BIGINT AUTO_INCREMENT works fine either way, so this variant just
# swaps in INTEGER for SQLite to keep tests working.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class HrmsBase(DeclarativeBase):
    """Separate declarative base from the KMS module's Base - these are two distinct
    MySQL databases (this one is `mksvision_mkswebsite_new`, the ported Laravel app's
    own database; KMS uses `lmsdev`) and must have independent metadata so Alembic can
    target each one separately."""


hrms_engine = create_async_engine(
    hrms_settings.sqlalchemy_database_uri,
    echo=hrms_settings.hrms_db_echo,
    pool_pre_ping=True,
    connect_args=hrms_settings.sqlalchemy_connect_args,
)

HrmsAsyncSessionLocal = async_sessionmaker(bind=hrms_engine, expire_on_commit=False, autoflush=False)


async def get_hrms_db() -> AsyncGenerator[AsyncSession, None]:
    async with HrmsAsyncSessionLocal() as session:
        yield session
