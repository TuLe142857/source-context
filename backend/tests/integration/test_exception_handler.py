"""Integration tests for application exception handling."""

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import ApplicationError
from app.main import create_app


def test_application_error_is_returned_as_json(
    test_settings: Settings,
) -> None:
    """Expected application errors should use the common error schema."""

    application: FastAPI = create_app(test_settings)

    @application.get("/_test/application-error")
    def raise_application_error() -> None:
        raise ApplicationError(
            code="test_error",
            message="Test application error.",
            status_code=status.HTTP_409_CONFLICT,
        )

    with TestClient(application) as client:
        response = client.get("/_test/application-error")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "code": "test_error",
        "message": "Test application error.",
    }
