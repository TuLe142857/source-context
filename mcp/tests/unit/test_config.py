"""Unit tests for MCP server configuration management."""

from pathlib import Path

import pytest

from source_context_mcp.config import (
    ConfigSchema,
    get_project_id_for_dir,
    load_config,
    save_config,
    set_api_key,
    set_project_id_for_dir,
)


def test_config_schema_defaults() -> None:
    """Tests default values of ConfigSchema instance."""
    cfg = ConfigSchema()
    assert cfg.server_url == "http://localhost:8000/api/v1"
    assert cfg.api_key is None
    assert cfg.active_project_id is None
    assert cfg.workspace_projects == {}


def test_save_and_load_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests saving configuration to disk and loading it back.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
    """
    config_file = tmp_path / "config.json"
    import source_context_mcp.config as cfg_module

    monkeypatch.setattr(cfg_module, "DEFAULT_CONFIG_PATH", config_file)

    cfg = ConfigSchema(
        server_url="http://testserver:8000/api/v1",
        api_key="sc_live_test123",
        active_project_id=42,
    )
    save_config(cfg)

    loaded = load_config()
    assert loaded.server_url == "http://testserver:8000/api/v1"
    assert loaded.api_key == "sc_live_test123"
    assert loaded.active_project_id == 42


def test_workspace_project_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests setting and retrieving workspace project ID mappings.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
    """
    config_file = tmp_path / "config.json"
    import source_context_mcp.config as cfg_module

    monkeypatch.setattr(cfg_module, "DEFAULT_CONFIG_PATH", config_file)

    dir_a = str((tmp_path / "repoA").resolve())
    dir_b = str((tmp_path / "repoB").resolve())

    set_project_id_for_dir(dir_a, 101)
    set_project_id_for_dir(dir_b, 202)

    assert get_project_id_for_dir(dir_a) == 101
    assert get_project_id_for_dir(dir_b) == 202


def test_set_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests setting API key and updating configuration.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
    """
    config_file = tmp_path / "config.json"
    import source_context_mcp.config as cfg_module

    monkeypatch.setattr(cfg_module, "DEFAULT_CONFIG_PATH", config_file)

    set_api_key("sc_live_newsecret", "http://custom-url/api/v1")
    cfg = load_config()
    assert cfg.api_key == "sc_live_newsecret"
    assert cfg.server_url == "http://custom-url/api/v1"
