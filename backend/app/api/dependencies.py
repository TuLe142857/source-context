"""Shared FastAPI dependencies."""

from typing import cast

from fastapi import Request

from app.core.config import Settings


def get_app_settings(request: Request) -> Settings:
    """Return settings associated with the current application instance."""

    return cast(Settings, request.app.state.settings)
