"""Application exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorResponse


class ApplicationError(Exception):
    """Base exception for expected application-level failures."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)

        self.code = code
        self.message = message
        self.status_code = status_code


async def application_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert an ApplicationError into a standard JSON response."""

    if not isinstance(exc, ApplicationError):
        raise exc

    response = ErrorResponse(
        code=exc.code,
        message=exc.message,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register application exception handlers."""

    application.add_exception_handler(
        ApplicationError,
        application_error_handler,
    )
