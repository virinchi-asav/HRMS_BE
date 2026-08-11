from fastapi import Request

from app.core.config import settings


def build_public_url(request: Request, relative_path: str) -> str:
    """Rewrites an on-disk relative path into a publicly-reachable HTTP URL.

    Mirrors the Java code's `InetAddress.getLocalHost()` + `server.port` URL building
    (used for both profile images and content-library file paths), but prefers an
    explicitly configured PUBLIC_HOST/PUBLIC_PORT for real deployments and falls back to
    the incoming request's own host when unset (e.g. local dev).
    """
    relative_path = relative_path.replace("\\", "/")
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path

    if settings.public_host:
        port = settings.public_port or settings.server_port
        return f"http://{settings.public_host}:{port}{relative_path}"

    base = str(request.base_url).rstrip("/")
    return f"{base}{relative_path}"
