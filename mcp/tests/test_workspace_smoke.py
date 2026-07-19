"""Smoke tests for the MCP workspace package."""

from importlib import import_module


def test_mcp_package_is_importable() -> None:
    """The MCP package should be installed by the workspace."""
    module = import_module("source_context_mcp")

    assert module.__package__ == "source_context_mcp"
