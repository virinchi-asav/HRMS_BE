"""Moves the legacy KMS files the user has dropped into ./kms_uploads (still sitting in
whatever ad-hoc folder names they were placed under) into the exact path convention the
app itself uses (file_storage_service.build_content_path:
{root}/{department_name}/{account_name}/{category_name}/{sub_category_name}/{file_name},
with "All"/"General" fallbacks matching content_service.upload_file), then updates each
matched mks_lms_content.fileUrl from its old E:\\Java\\... path to the new one.

Matching a row to a file on disk can't rely on the row's OLD department/account folder
names (e.g. old "IT" vs the ad-hoc folder the user made, "IT Services") since those drifted
over time - only the filename is trustworthy, plus the immediate parent folder name
(subcategory) to break ties when two rows share a filename (confirmed to happen exactly
once: "Yak User Documentation 2024.docx" under two different subcategories).

Rows with no matching file on disk are left untouched (fileUrl keeps pointing at the old
dead path) rather than guessed at - this script only ever touches rows it found a real
file for.

A single physical file can satisfy more than one DB row (confirmed: fileId 56 and 346 are
two distinct catalogue entries - different department/account/category assignments - that
both point at a file named "Fraud Prediction Model.pdf", and only one copy of it exists on
disk). So sources are always copied, never moved, while iterating rows; the now-redundant
staging copies are deleted only in a final cleanup pass once every row has been resolved.
"""
import asyncio
import os
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.constants import SENTINEL_ID

UPLOADS_ROOT = Path(settings.file_storage_root)


def resolve_name(id_: int | None, names: dict[int, str], default: str) -> str:
    if id_ is None or id_ == SENTINEL_ID:
        return default
    return names.get(id_, default)


async def main():
    engine = create_async_engine(settings.sqlalchemy_database_uri)

    async with engine.connect() as conn:
        dept_rows = await conn.exec_driver_sql("SELECT departmentId, departmentName FROM mks_kms_department")
        departments = dict(list(dept_rows))
        acct_rows = await conn.exec_driver_sql("SELECT accountId, accountName FROM mks_kms_account")
        accounts = dict(list(acct_rows))
        cat_rows = await conn.exec_driver_sql("SELECT categoryId, categoryName FROM mks_kms_category")
        categories = dict(list(cat_rows))
        sub_rows = await conn.exec_driver_sql("SELECT subCategoryId, subCategoryName FROM mks_kms_subcategory")
        subcategories = dict(list(sub_rows))

        content_rows = await conn.exec_driver_sql(
            "SELECT fileId, fileName, fileUrl, department, account, category, subCategory FROM mks_lms_content"
        )
        content = list(content_rows)

    # Index every file currently under kms_uploads by basename, since the folders the user
    # placed things in don't necessarily match this app's naming for department/account.
    disk_index: dict[str, list[Path]] = {}
    for root, _dirs, files in os.walk(UPLOADS_ROOT):
        for fn in files:
            disk_index.setdefault(fn, []).append(Path(root) / fn)

    updated, unmatched, ambiguous = [], [], []
    sources_used: set[Path] = set()
    targets_created: set[Path] = set()

    async with engine.begin() as conn:
        for file_id, file_name, old_url, dept_id, acct_id, cat_id, subcat_id in content:
            candidates = disk_index.get(file_name, [])
            if not candidates:
                unmatched.append(file_name)
                continue

            if len(candidates) == 1:
                source = candidates[0]
            else:
                old_parent = old_url.rsplit("\\", 2)[-2] if "\\" in old_url else None
                tie_break = [c for c in candidates if c.parent.name == old_parent]
                if len(tie_break) == 1:
                    source = tie_break[0]
                else:
                    ambiguous.append((file_name, [str(c) for c in candidates]))
                    continue

            dept_name = resolve_name(dept_id, departments, "All")
            acct_name = resolve_name(acct_id, accounts, "All")
            cat_name = categories.get(cat_id, "General")
            subcat_name = resolve_name(subcat_id, subcategories, "General")

            target = UPLOADS_ROOT / dept_name / acct_name / cat_name / subcat_name / file_name

            if source.resolve() != target.resolve():
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(str(source), str(target))
            sources_used.add(source)
            targets_created.add(target.resolve())

            new_url = str(target)
            await conn.exec_driver_sql(
                "UPDATE mks_lms_content SET fileUrl = %s WHERE fileId = %s", (new_url, file_id)
            )
            updated.append((file_id, file_name, new_url, str(source), new_url))

    # Every source has now been copied into its canonical home(s) for every DB row that
    # referenced it - the staging copy the user dropped in is redundant, so remove it and
    # then prune whatever ad-hoc folders that leaves empty. Except when a source's path
    # *is* one of the canonical targets (the row's own home was already where the file
    # was placed) - deleting that would destroy the very file other rows just got copied
    # from, so it's kept.
    for source in sources_used:
        if source.resolve() in targets_created:
            continue
        try:
            source.unlink()
        except OSError:
            pass
    for root, dirs, files in os.walk(UPLOADS_ROOT, topdown=False):
        if not dirs and not files and Path(root) != UPLOADS_ROOT:
            try:
                os.rmdir(root)
            except OSError:
                pass

    await engine.dispose()

    print(f"DB rows total: {len(content)}")
    print(f"Files placed on disk: {sum(len(v) for v in disk_index.values())}")
    print(f"Matched and updated: {len(updated)}")
    print(f"Ambiguous (needs manual resolution): {len(ambiguous)}")
    for name, paths in ambiguous:
        print(f"  {name}: {paths}")
    print(f"No file provided (left untouched): {len(unmatched)}")

    print("\n--- Updated rows ---")
    for file_id, name, url, source, target in updated:
        print(f"  [{file_id}] {name}: {source} -> {target}")


if __name__ == "__main__":
    asyncio.run(main())
