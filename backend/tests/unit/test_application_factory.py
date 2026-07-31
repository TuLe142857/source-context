"""Tests for the FastAPI application factory."""

from app.core.config import Settings
from app.main import create_app


def test_create_app_applies_provided_settings(
    test_settings: Settings,
) -> None:
    """The application factory should use the provided settings."""

    application = create_app(test_settings)

    assert application.title == test_settings.app_name
    assert application.version == test_settings.app_version
    assert application.debug is test_settings.debug
    assert application.state.settings is test_settings


def test_create_app_registers_health_route(
    test_settings: Settings,
) -> None:
    """The application should expose the health-check route."""

    application = create_app(test_settings)
    openapi_schema = application.openapi()

    assert "/health" in openapi_schema["paths"]
    assert "get" in openapi_schema["paths"]["/health"]
