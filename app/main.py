import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routers import account, category, content, department, static_files, subcategory, user_types
from app.core.exceptions import register_exception_handlers
from app.db.session import AsyncSessionLocal, engine
from app.hrms.core.config import hrms_settings
from app.hrms.db import hrms_engine
from app.services.account_service import get_or_create_bench_account
from app.hrms.routers import (
    admin as hrms_admin,
    auth as hrms_auth,
    candidates as hrms_candidates,
    certificates as hrms_certificates,
    clients as hrms_clients,
    contact as hrms_contact,
    current_openings as hrms_current_openings,
    jobs as hrms_jobs,
    reports as hrms_reports,
    skill_configurations as hrms_skill_configurations,
    skills as hrms_skills,
    survey as hrms_survey,
    task_assessment as hrms_task_assessment,
    testimonials as hrms_testimonials,
    training as hrms_training,
    users as hrms_users,
    webhooks as hrms_webhooks,
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    async with hrms_engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    async with AsyncSessionLocal() as session:
        await get_or_create_bench_account(session)
    yield


app = FastAPI(title="HRMS Backend", version="1.0.0", lifespan=lifespan)

# Mirrors the Java app's permissive CORS config (allow all origins/methods/headers).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

register_exception_handlers(app)

# --- KMS module (Java conversion) - authenticates via the single HRMS login now, see
# app/core/deps.py's get_current_user and app/hrms/core/constants.py's HRMS_TO_KMS_ROLE ---
app.include_router(account.router)
app.include_router(category.router)
app.include_router(department.router)
app.include_router(subcategory.router)
app.include_router(content.router)
app.include_router(user_types.router)

# --- HRMS module (Laravel conversion) ---
app.include_router(hrms_auth.router)
app.include_router(hrms_clients.router)
app.include_router(hrms_jobs.router)
app.include_router(hrms_jobs.public_router)
app.include_router(hrms_current_openings.router)
app.include_router(hrms_skill_configurations.router)
app.include_router(hrms_skills.router)
app.include_router(hrms_candidates.router)
app.include_router(hrms_candidates.public_router)
app.include_router(hrms_users.router)
app.include_router(hrms_survey.router)
app.include_router(hrms_survey.admin_router)
app.include_router(hrms_testimonials.router)
app.include_router(hrms_admin.router)
app.include_router(hrms_admin.requests_router)
app.include_router(hrms_webhooks.router)
app.include_router(hrms_contact.router)
app.include_router(hrms_training.router)
app.include_router(hrms_certificates.router)
app.include_router(hrms_task_assessment.router)
app.include_router(hrms_reports.router)

# Public file serving for HRMS uploads (resumes, profile photos, skill attachments) -
# mirrors Laravel's public/uploads convention (no access control there either).
app.mount("/hrms-uploads", StaticFiles(directory=hrms_settings.hrms_upload_root, check_dir=False), name="hrms-uploads")

# Catch-all static file server (KMS) - must be registered last so it never shadows an /api/* route.
app.include_router(static_files.router)
