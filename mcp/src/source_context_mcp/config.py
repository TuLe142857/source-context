"""Configuration management for Source Context MCP Server."""

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIR = Path.home() / ".source_context"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_SERVER_URL = "http://localhost:8000/api/v1"


class ConfigSchema:
    """Data schema representing MCP configuration settings.

    Attributes:
        server_url: Base URL of the FastAPI backend.
        api_key: Personal Access Token (PAT) for backend authentication.
        active_project_id: Default fallback active project ID.
        workspace_projects: Mapping of absolute workspace folder paths to project IDs.
    """

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        api_key: str | None = None,
        active_project_id: int | None = None,
        workspace_projects: dict[str, int] | None = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.active_project_id = active_project_id
        self.workspace_projects = workspace_projects if workspace_projects is not None else {}

    def to_dict(self) -> dict[str, Any]:
        """Converts configuration object into a serializable dictionary.

        Returns:
            dict[str, Any]: Dictionary representation of configuration.
        """
        return {
            "server_url": self.server_url,
            "api_key": self.api_key,
            "active_project_id": self.active_project_id,
            "workspace_projects": self.workspace_projects,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigSchema":
        """Creates ConfigSchema instance from a dictionary.

        Args:
            data: Raw dictionary loaded from JSON.

        Returns:
            ConfigSchema: Instantiated configuration object.
        """
        return cls(
            server_url=data.get("server_url", DEFAULT_SERVER_URL),
            api_key=data.get("api_key"),
            active_project_id=data.get("active_project_id"),
            workspace_projects=data.get("workspace_projects", {}),
        )


def get_config_path() -> Path:
    """Returns absolute path to the configuration file.

    Returns:
        Path: Configuration file path.
    """
    return DEFAULT_CONFIG_PATH


def load_config() -> ConfigSchema:
    """Loads configuration from local disk.

    If file does not exist, returns default configuration.

    Returns:
        ConfigSchema: Loaded configuration.
    """
    path = get_config_path()
    if not path.exists():
        return ConfigSchema()

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return ConfigSchema.from_dict(data)
    except (json.JSONDecodeError, OSError):
        return ConfigSchema()


def save_config(config: ConfigSchema) -> None:
    """Saves configuration to local disk.

    Args:
        config: Configuration object to write.
    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)


def get_project_id_for_dir(dir_path: str) -> int | None:
    """Retrieves project ID mapped to a specific workspace directory path.

    Args:
        dir_path: Absolute directory path.

    Returns:
        int | None: Mapped project ID or active_project_id fallback if not set.
    """
    config = load_config()
    normalized_path = str(Path(dir_path).resolve())
    if normalized_path in config.workspace_projects:
        return config.workspace_projects[normalized_path]
    return config.active_project_id


def set_project_id_for_dir(dir_path: str, project_id: int) -> None:
    """Sets and saves project ID mapping for a workspace directory path.

    Args:
        dir_path: Absolute directory path.
        project_id: Target project ID.
    """
    config = load_config()
    normalized_path = str(Path(dir_path).resolve())
    config.workspace_projects[normalized_path] = project_id
    config.active_project_id = project_id
    save_config(config)


def set_api_key(api_key: str, server_url: str | None = None) -> None:
    """Updates API key and optional server URL in configuration.

    Args:
        api_key: Personal Access Token secret string.
        server_url: Base FastAPI server URL.
    """
    config = load_config()
    config.api_key = api_key
    if server_url is not None:
        config.server_url = server_url.rstrip("/")
    save_config(config)
