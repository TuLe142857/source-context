"""Smoke tests for the backend workspace package."""

from importlib import import_module


def test_backend_app_package_is_importable() -> None:
    """The backend application package should be installed by the workspace."""
    module = import_module("app")

    assert module.__package__ == "app"


def test_backend_workers_package_is_importable() -> None:
    """The worker package should be installed by the workspace."""
    module = import_module("workers")

    assert module.__package__ == "workers"
