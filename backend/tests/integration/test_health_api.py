"""Integration tests for the backend health API."""

from fastapi import status
from fastapi.testclient import TestClient


def test_health_endpoint_returns_backend_status(
    client: TestClient,
) -> None:
    """The health endpoint should return application metadata."""

    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "service": "Source Context Backend Test",
        "version": "0.1.0-test",
        "environment": "test",
    }
