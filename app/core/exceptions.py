import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.constants import STATUS_ERROR

logger = logging.getLogger("app")


class ServiceException(Exception):
    """Mirrors com.mks.lms.exceptions.ServiceException - mapped to HTTP 400 globally."""


class DataNotFoundException(Exception):
    """Mirrors com.mks.lms.exceptions.DataNotFoundException.

    In the Java app this has no global handler; callers catch it locally
    (e.g. file upload -> 404). Keep that same local-handling convention here.
    """


class FileAlreadyExistsException(Exception):
    """Mirrors java.nio.file.FileAlreadyExistsException as used by FileUploadImpl."""


class UserFoundException(Exception):
    """Mirrors com.mks.lms.exceptions.UserFoundException (email already registered)."""


class UserUnauthorizedException(Exception):
    """Mirrors com.mks.lms.exceptions.UserUnauthorizedException."""


class ValidationException(Exception):
    """Mirrors com.mks.lms.exceptions.ValidationException."""


class AuthEntryPointException(Exception):
    """Raised when a request is missing/has an invalid JWT. Mirrors AuthEntryPointJwt."""

    def __init__(self, path: str, message: str = "Full authentication is required to access this resource"):
        self.path = path
        self.message = message
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = {}
        for error in exc.errors():
            field = error["loc"][-1] if error["loc"] else "body"
            errors[str(field)] = error["msg"]
        logger.error("Invalid request parameters: %s", errors)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(errors), "status": STATUS_ERROR, "data": None},
        )

    @app.exception_handler(ServiceException)
    async def handle_service_exception(request: Request, exc: ServiceException) -> JSONResponse:
        logger.error("ServiceException: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(exc), "status": STATUS_ERROR, "data": None},
        )

    @app.exception_handler(AuthEntryPointException)
    async def handle_auth_entry_point(request: Request, exc: AuthEntryPointException) -> JSONResponse:
        logger.error("Unauthorized error: %s", exc.message)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": status.HTTP_401_UNAUTHORIZED,
                "error": "Unauthorized",
                "message": exc.message,
                "path": exc.path,
            },
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(exc), "status": STATUS_ERROR, "data": None},
        )
