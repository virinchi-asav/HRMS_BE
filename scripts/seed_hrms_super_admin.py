"""One-off script: creates (or updates) an Admin (role=1, HRMS's top role) user in the
HRMS database.

Usage (from the HRMS_Backend directory, with your real .env already filled in):
    python scripts/seed_hrms_super_admin.py

Reads DB connection info from the same .env / Settings the app itself uses
(app/hrms/core/config.py) - make sure HRMS_DB_HOST/HRMS_DB_PORT/HRMS_DB_NAME/
HRMS_DB_USER/HRMS_DB_PASSWORD point at your real MySQL server (mksvision_mkswebsite_new)
before running this. Safe to re-run: if the user already exists, this just resets their
password and role rather than erroring.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.hrms.core.security import hash_password
from app.hrms.db import HrmsAsyncSessionLocal
from app.hrms.models.user import UserEntity

EMAIL = "akash.v@mksvision.com"
PASSWORD = "Akashvel98@kum"
NAME = "Akash V"
ADMIN_ROLE = 1  # HRMS's top role - see app/hrms/core/constants.py:Role.ADMIN


async def main() -> None:
    async with HrmsAsyncSessionLocal() as session:
        result = await session.execute(select(UserEntity).where(UserEntity.email == EMAIL))
        user = result.scalar_one_or_none()

        if user is None:
            user = UserEntity(
                name=NAME,
                email=EMAIL,
                password=hash_password(PASSWORD),
                role=ADMIN_ROLE,
                can_update=True,
            )
            session.add(user)
            print(f"Creating new HRMS user {EMAIL} with role Admin (1).")
        else:
            user.password = hash_password(PASSWORD)
            user.role = ADMIN_ROLE
            print(f"HRMS user {EMAIL} already exists - password reset and role set to Admin (1).")

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
