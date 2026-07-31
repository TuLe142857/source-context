from datetime import datetime
from typing import Annotated, Any, Literal, Mapping, Sequence

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from .error_code import ErrorCode


class ResponseSuccessSchema[T](BaseModel):
    success: Annotated[
        Literal[True], Field(description="Always true for success response")
    ]
    data: Annotated[T, Field(description="Response data")]
    message: Annotated[
        str | None, Field(description="Optional, message to display to user")
    ]


class PaginationMeta(BaseModel):
    """
    Class provide pagination metadata
    """

    current_page: Annotated[int, Field(ge=0, description="Current page number")]
    per_page: Annotated[int, Field(ge=0, description="Number of items per page")]
    total_items: Annotated[int, Field(ge=0, description="Total number of items")]
    total_pages: Annotated[int, Field(ge=0, description="Total number of pages")]
    has_next: Annotated[bool, Field(description="Whether the next page is available")]
    has_prev: Annotated[
        bool, Field(description="Whether the previous page is available")
    ]


class ResponsePaginationSchema[T](ResponseSuccessSchema[T]):
    """
    Custom response class to return list objects with pagination.
    """

    data: Annotated[Sequence[T], Field(description="List of object")]
    meta: Annotated[PaginationMeta, Field(description="Pagination metadata")]


class ResponseErrorSchema(BaseModel):
    success: Annotated[Literal[False], Field("Always false for error response")]
    error_code: Annotated[
        str, Field(description="Error code, give client more info about error")
    ]
    message: Annotated[
        str | None, Field(description="Optional, message to display to user")
    ]


def build_error_docs(
    *errors: ErrorCode | tuple[ErrorCode, str],
) -> dict[int | str, dict[str, Any]]:
    """
     Build OpenAPI-compatible error response documentation for FastAPI endpoints
    Args:
        *errors: list of [ErrorCode | tuple[ErrorCode, message]]

    Returns:
        A dictionary mapping HTTP status codes to their OpenAPI response definitions.

    Examples:
        >>> from fastapi import APIRouter
        >>> router = APIRouter()
        >>>
        >>> @router.get(
        >>>     "/data",
        >>>     response_model=ResponseSuccessSchema,
        >>>     responses = build_error_docs(ErrorCode.VALIDATION_ERROR)
        >>> )
        >>> def some_func():
        >>>     pass
    """
    responses: dict[int | str, dict[str, Any]] = {}

    for item in errors:
        if isinstance(item, ErrorCode):
            err = item
            msg = err.name.replace("_", " ").capitalize()
        else:
            err, msg = item

        status = err.status_code

        if status not in responses:
            responses[status] = {
                "description": f"Error {status}",
                "model": ResponseErrorSchema,
                "content": {"application/json": {"examples": {}}},
            }

        responses[status]["content"]["application/json"]["examples"][err.error_code] = {
            "summary": err.error_code,
            "value": {"success": False, "error_code": err.error_code, "message": msg},
        }

    return responses


class APIResponse(JSONResponse):
    """
    Use:
        ApiResponse.ok() for success response(JSON body will be built as  ResponseSuccessSchema).
        ApiResponse.error() for error response(JSON body will be built as  ResponseErrorSchema).
    """

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Copy from supper class __init__.
        Do not use this.
        Use APIResponse.ok() or APIResponse.paginate() or APIResponse.error() instead.
        """
        super().__init__(content, status_code, headers, media_type, background)

    @staticmethod
    def ok(
        data: Any = None, message: str | None = None, status_code: int = 200
    ) -> "APIResponse":
        """
        Build JSON response for success response.
        Body will be built as ResponseSuccessSchema.
        """
        body = {
            "success": True,
            "data": jsonable_encoder(data),
            "message": message,
        }
        return APIResponse(content=body, status_code=status_code)

    @staticmethod
    def paginate(
        current_page: int,
        per_page: int,
        total_items: int,
        data: Sequence[Any] | None = None,
        message: str | None = None,
        status_code: int = 200,
    ) -> "APIResponse":
        """
        Build JSON response for error response.
        Body will be built as ResponsePaginationSchema.
        """
        total_pages = (total_items + per_page - 1) // per_page
        if data is None:
            data = []
        body = {
            "success": True,
            "message": message,
            "meta": {
                "current_page": current_page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": current_page < total_pages,
                "has_prev": current_page > 1,
            },
            "data": jsonable_encoder(data),
        }
        return APIResponse(content=body, status_code=status_code)

    @staticmethod
    def error(
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR, message: str | None = None
    ) -> "APIResponse":
        """
        Build JSON response for error response.
        Body will be built as ResponseErrorSchema.
        """
        body = {
            "success": False,
            "error_code": error_code.error_code,
            "message": message,
        }
        return APIResponse(
            content=body,
            status_code=error_code.status_code,
        )

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] | None = "lax",
        partitioned: bool = False,
    ) -> "APIResponse":
        """
        This method call super().set_cookie() but return self for builder pattern.
        """
        super().set_cookie(
            key,
            value,
            max_age,
            expires,
            path,
            domain,
            secure,
            httponly,
            samesite,
            partitioned,
        )
        return self

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] | None = "lax",
    ) -> "APIResponse":
        """
        This method call super().delete_cookie() but return self for builder pattern.
        """
        super().delete_cookie(key, path, domain, secure, httponly, samesite)
        return self

    def set_header(self, key: str, value: str) -> "APIResponse":
        self.headers[key] = value
        return self
