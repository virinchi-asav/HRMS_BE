import logging
import uuid
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


def build_content_path(
    root: str, department_name: str, account_name: str, category_name: str, sub_category_name: str, file_name: str
) -> Path:
    """Mirrors FileUploadImpl's disk layout: {root}/{dept}/{account}/{category}/{subCategory}/{file}."""
    return Path(root) / department_name / account_name / category_name / sub_category_name / file_name


def build_edit_dir(root: str, department_name: str, account_name: str, category_name: str) -> Path:
    """Mirrors editFile's new-folder layout (no sub-category segment, per the Java code)."""
    return Path(root) / department_name / account_name / category_name


async def write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)


async def read_file(path: Path) -> bytes:
    async with aiofiles.open(path, "rb") as f:
        return await f.read()


def delete_file(path: Path) -> bool:
    try:
        Path(path).unlink()
        return True
    except OSError as e:
        logger.error("Exception occurred while removing file: %s", e)
        return False


async def move_file(old_path: Path, new_path: Path) -> None:
    """Mirrors editFile's editFilePath: read old bytes, write to new location, delete old."""
    content = await read_file(old_path)
    await write_file(new_path, content)
    delete_file(old_path)


async def save_profile_image(profile_images_dir: str, original_filename: str, content: bytes) -> str:
    directory = Path(profile_images_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid.uuid4()}_{original_filename}"
    await write_file(path, content)
    return str(path)


def delete_profile_image(path: str) -> None:
    try:
        Path(path).unlink()
    except OSError as e:
        logger.error("An exception occurred while deleting the old profile image: %s", e)
