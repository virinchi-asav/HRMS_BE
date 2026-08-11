from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

# Mirrors Spring Boot's static-resource serving configured via
# spring.web.resources.static-locations=file:///{filepath},file:///{profileimagespath}
# (WebSecurityConfig permits a handful of representative path shapes, but the actual
# handler serves any matching relative path from either configured root, in order) -
# hence a single catch-all route tried against both roots, rather than a fixed set of
# path-depth-specific routes.
#
# NOTE (flagged, not fixed here): this is unauthenticated by design constraint, not by
# oversight - every reference to a file's URL in the frontend (KMS file preview,
# certificate template images, training screenshots, candidate resumes) is a plain
# <img>/<video>/<iframe> src, which the browser fetches with no Authorization header at
# all. Requiring a bearer token here would 401 every one of those previews. Closing this
# gap for real needs a signed, short-lived query-token scheme (minted alongside
# build_public_url, verified here) - a deliberate follow-up, not a one-line dependency.
router = APIRouter(tags=["static-files"])

_ROOTS = [settings.file_storage_root, settings.profile_images_path]


@router.get("/{file_path:path}")
async def serve_static_file(file_path: str):
    for root in _ROOTS:
        root_path = Path(root).resolve()
        candidate = (root_path / file_path).resolve()
        if root_path in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
    raise HTTPException(status_code=404, detail="File not found")
