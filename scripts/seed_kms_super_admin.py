"""One-off script: creates (or updates) a SUPER_ADMIN user in the KMS database.

Usage (from the HRMS_Backend directory, with your real .env already filled in):
    python scripts/seed_kms_super_admin.py

Reads DB connection info from the same .env / Settings the app itself uses
(app/core/config.py) - make sure DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD point at
your real MySQL server before running this. Safe to re-run: if the user already
exists, this just resets their password and (re)assigns the SUPER_ADMIN role rather
than erroring.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.role import RoleEntity
from app.models.user import UserEntity

EMAIL = "akash.v@mksvision.com"
PASSWORD = "Akashvel98@kum"
NAME = "Akash V"
ROLE_NAME = "SUPER_ADMIN"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        role_result = await session.execute(select(RoleEntity).where(RoleEntity.role_name == ROLE_NAME))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = RoleEntity(role_name=ROLE_NAME)
            session.add(role)
            await session.flush()
            print(f"Created role '{ROLE_NAME}'.")

        user_result = await session.execute(select(UserEntity).where(UserEntity.email == EMAIL))
        user = user_result.scalar_one_or_none()

        if user is None:
            user = UserEntity(
                user_name=NAME,
                email=EMAIL,
                password=hash_password(PASSWORD),
                enabled=True,
                password_reset_required=False,
            )
            user.role = role
            session.add(user)
            print(f"Creating new KMS user {EMAIL} with role {ROLE_NAME}.")
        else:
            user.password = hash_password(PASSWORD)
            user.enabled = True
            user.role = role
            print(f"KMS user {EMAIL} already exists - password reset and role set to {ROLE_NAME}.")

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
