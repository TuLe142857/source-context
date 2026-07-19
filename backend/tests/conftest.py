"""Shared backend test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Return deterministic settings for backend tests."""

    return Settings(
        app_name="Source Context Backend Test",
        app_version="0.1.0-test",
        environment="test",
        debug=False,
        log_level="WARNING",
        api_v1_prefix="/api/v1",
    )


@pytest.fixture
def application(test_settings: Settings) -> FastAPI:
    """Create a new FastAPI application for each test."""

    return create_app(test_settings)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    """Return a synchronous API test client."""

    with TestClient(application) as test_client:
        yield test_client
