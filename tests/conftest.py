import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.hrms.core.constants import Role
from app.hrms.core.security import hash_password as hrms_hash_password
from app.hrms.db import get_hrms_db
from app.hrms.models import HrmsBase
from app.hrms.models.user import UserEntity as HrmsUserEntity
from app.main import app
from app.models import Base
from app.models.account import AccountEntity
from app.models.department import DepartmentEntity
from app.models.user_type import UserTypeEntity

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

hrms_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
HrmsTestSessionLocal = async_sessionmaker(bind=hrms_test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


async def _override_get_hrms_db():
    async with HrmsTestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db
app.dependency_overrides[get_hrms_db] = _override_get_hrms_db


@pytest_asyncio.fixture(autouse=True)
async def _stub_email_sending(monkeypatch):
    """Real SMTP credentials are configured for this app - without this stub, every
    test that creates a user/training/task (all of which now trigger notification
    emails) would attempt a real send to fake @example.com addresses through the real
    mailbox. Patching aiosmtplib.send itself (rather than email_service.send_email)
    means the retry/error-handling path in email_service is still exercised for free."""

    async def _fake_send(*args, **kwargs):
        return None

    monkeypatch.setattr("aiosmtplib.send", _fake_send)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with hrms_test_engine.begin() as conn:
        await conn.run_sync(HrmsBase.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with hrms_test_engine.begin() as conn:
        await conn.run_sync(HrmsBase.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_lookups():
    """Seeds a department/account/user_type triplet reused by several tests."""
    async with TestSessionLocal() as session:
        department = DepartmentEntity(department_name="Engineering", department_description="Eng dept")
        account = AccountEntity(account_name="Acme", account_description="Acme account")
        user_type = UserTypeEntity(type_name="MANAGEMENT")
        session.add_all([department, account, user_type])
        await session.commit()
        await session.refresh(department)
        await session.refresh(account)
        await session.refresh(user_type)
        return {
            "department_id": department.department_id,
            "account_id": account.account_id,
            "user_type_id": user_type.id,
        }


@pytest_asyncio.fixture
async def auth_token(seed_lookups):
    """KMS now authenticates via the HRMS login - creates an HRMS user with role=ADMIN
    (maps to KMS SUPER_ADMIN via HRMS_TO_KMS_ROLE) and the 3 KMS-scoping columns set,
    and returns a bearer token for it via /api/hrms/auth/login."""
    async with HrmsTestSessionLocal() as session:
        user = HrmsUserEntity(
            name="Admin User",
            email="admin@example.com",
            password=hrms_hash_password("password123"),
            role=Role.ADMIN,
            can_update=True,
            kms_department_id=seed_lookups["department_id"],
            kms_account_id=seed_lookups["account_id"],
            kms_user_type_id=seed_lookups["user_type_id"],
        )
        session.add(user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/hrms/auth/login", json={"email": "admin@example.com", "password": "password123"}
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]


@pytest_asyncio.fixture
async def hrms_admin_token():
    """Creates an HRMS Admin (role=1) user directly in the DB and returns a bearer token."""
    async with HrmsTestSessionLocal() as session:
        user = HrmsUserEntity(
            name="HRMS Admin",
            email="hrms-admin@example.com",
            password=hrms_hash_password("password123"),
            role=1,
            can_update=True,
        )
        session.add(user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/hrms/auth/login", json={"email": "hrms-admin@example.com", "password": "password123"}
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]


@pytest_asyncio.fixture
async def hrms_user_factory():
    """Returns an async factory creating an HRMS user with an arbitrary role and
    returning (user_id, bearer_token) - reused by tests needing several distinct
    role-holders (e.g. one or more Trainers, a Trainee, and a BU Head for the training
    workflow)."""

    async def _create(name: str, email: str, role: int) -> tuple[int, str]:
        async with HrmsTestSessionLocal() as session:
            user = HrmsUserEntity(
                name=name,
                email=email,
                password=hrms_hash_password("password123"),
                role=role,
                can_update=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/hrms/auth/login", json={"email": email, "password": "password123"})
            assert response.status_code == 200, response.text
            return user_id, response.json()["access_token"]

    return _create
