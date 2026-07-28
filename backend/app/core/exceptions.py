"""Application exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlalchemy.exc import IntegrityError

from .response import APIResponse
from .error_code import ErrorCode


class AppException(Exception):
    """Base exception for expected application-level failures."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        message: str | None = None,
    ) -> None:
        self.__error_code = error_code
        if message is not None:
            self.__message = message
        else:
            self.__message = error_code.name.lower().replace("_", " ").capitalize()

        super().__init__(message)

    @property
    def error_code(self) -> ErrorCode:
        return self.__error_code

    @property
    def message(self) -> str | None:
        return self.__message


def register_exception_handlers(app: FastAPI) -> None:
    """Register application exception handlers."""

    @app.exception_handler(AppException)
    def app_exception_handler(request: Request, exc: AppException) -> APIResponse:
        return APIResponse.error(exc.error_code, exc.message)

    @app.exception_handler(IntegrityError)
    def sqlalchemy_integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> APIResponse:
        return APIResponse.error(ErrorCode.DATA_INTEGRITY_ERROR, str(exc))

    @app.exception_handler(RequestValidationError)
    def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> APIResponse:
        return APIResponse.error(ErrorCode.VALIDATION_ERROR, str(exc.errors()))

    @app.exception_handler(HTTPException)
    def http_exception_handler(request: Request, exc: HTTPException) -> APIResponse:
        return APIResponse.error(ErrorCode.UNKNOWN_ERROR, str(exc))

    @app.exception_handler(Exception)
    def unexpected_exception_handler(request: Request, exc: Exception) -> APIResponse:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Unexpected exception occurred")
        return APIResponse.error(ErrorCode.UNKNOWN_ERROR, str(exc))
