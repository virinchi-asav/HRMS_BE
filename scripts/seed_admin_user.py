"""One-off script: creates (or updates) an Admin (role=1) user in the HRMS database.

Usage (from the HRMS_Backend directory):
    python scripts/seed_admin_user.py

Reads DB connection info from the same .env / Settings the app itself uses
(app/hrms/core/config.py). Safe to re-run: if the user already exists, this just
resets their password and role rather than erroring.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.hrms.core.security import hash_password
from app.hrms.db import HrmsAsyncSessionLocal
from app.hrms.models.user import UserEntity

EMAIL = "admin@mksvision.com"
PASSWORD = "Admin@123"
NAME = "Admin"
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
            user.name = NAME
            user.password = hash_password(PASSWORD)
            user.role = ADMIN_ROLE
            print(f"HRMS user {EMAIL} already exists - name/password reset and role set to Admin (1).")

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
