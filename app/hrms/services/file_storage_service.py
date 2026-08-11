import time
import uuid
from pathlib import Path

import aiofiles
from fastapi import Request

from app.hrms.core.config import hrms_settings

# All uploads live under hrms_settings.hrms_upload_root, mounted publicly at
# /hrms-uploads/... in main.py (StaticFiles) - mirrors Laravel's public/uploads
# convention (no access control was applied to these files in the source app either).


def user_document_dir(user_id: int, field_name: str) -> Path:
    """Mirrors public_path("uploads/users/{id}/{field}")."""
    return Path(hrms_settings.hrms_upload_root) / "users" / str(user_id) / field_name


def skill_attachment_dir(user_id: int, skill_slug: str, sub_skill_slug: str | None = None) -> Path:
    """Mirrors public_path("uploads/users/{userId}/skill/{slug}[/sub_skills/{subslug}]")."""
    base = Path(hrms_settings.hrms_upload_root) / "users" / str(user_id) / "skill" / skill_slug
    return base / "sub_skills" / sub_skill_slug if sub_skill_slug else base


def candidate_resume_dir() -> Path:
    return Path(hrms_settings.hrms_upload_root)


def training_material_dir(training_id: int) -> Path:
    return Path(hrms_settings.hrms_upload_root) / "training" / str(training_id)


def training_assessment_dir(training_id: int, assessment_id: int) -> Path:
    return Path(hrms_settings.hrms_upload_root) / "training" / str(training_id) / "assessments" / str(assessment_id)


def certificate_template_dir() -> Path:
    return Path(hrms_settings.hrms_upload_root) / "certificate-templates"


def training_certificate_dir(training_id: int) -> Path:
    return Path(hrms_settings.hrms_upload_root) / "training" / str(training_id) / "certificates"


async def save_file(directory: Path, filename: str, content: bytes) -> str:
    """Writes content to directory/filename, creating directories as needed. Returns
    just the stored filename (callers store this bare name in the DB column, matching
    the Laravel app's convention - the directory is reconstructable from the owning
    record's other fields)."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)
    return filename


def unique_filename(original_filename: str) -> str:
    """Mirrors `uniqid().time()` / `{time()}_{originalName}` collision-avoidance used
    throughout the Laravel controllers for uploaded file names."""
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{original_filename}"


def delete_file(path: Path) -> bool:
    try:
        Path(path).unlink()
        return True
    except OSError:
        return False


def build_public_url(request: Request, relative_path: str) -> str:
    relative_path = str(relative_path).replace("\\", "/").lstrip("/")
    base = str(request.base_url).rstrip("/")
    return f"{base}/hrms-uploads/{relative_path}"
