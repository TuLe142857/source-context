"""Common API response schemas."""

from typing import Literal

from pydantic import BaseModel

from app.core.config import Environment


class HealthResponse(BaseModel):
    """Response returned by the backend health endpoint."""

    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: Environment


class ErrorResponse(BaseModel):
    """Standard application error response."""

    code: str
    message: str
