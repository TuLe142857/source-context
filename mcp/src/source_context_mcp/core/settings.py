from functools import lru_cache
from pathlib import Path

import tomli_w
from pydantic import SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

CONFIG_DIR = Path.home() / ".source_context_mcp"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=str(CONFIG_FILE),
    )

    SERVER_URL: str = "default"
    """Server URL. Include prefix. Example: http://localhost:8000/mcp/v1"""

    PAT: SecretStr = SecretStr("Default")
    """Personal access token"""

    DEFAULT_WORKSPACE_ID: int = 1
    """Default Workspace ID"""

    PATH_WORKSPACE: dict[str, int] = {}
    PATH_REPO: dict[str, int] = {}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
        )


@lru_cache
def get_settings() -> Settings:
    """
    Get default settings.
        - See ``get_settings_with_overrides`` to see how to get settings with overrides values.
    Returns:

    """
    return Settings()


def get_settings_with_overrides(
    server_url_override: str | None = None,
    pat_override: SecretStr | str | None = None,
    default_workspace_id_override: int | None = None,
) -> Settings:
    """
    Get settings with overrides values. Any None value will be ignored.
        - This method does not change value of ``get_settings``
        - This method does not change default settings in config file.
    """

    fields_overrides = {}
    if server_url_override is not None:
        fields_overrides["SERVER_URL"] = server_url_override
    if pat_override is not None:
        fields_overrides["PAT"] = pat_override if isinstance(pat_override, SecretStr) else SecretStr(pat_override)
    if default_workspace_id_override is not None:
        fields_overrides["DEFAULT_WORKSPACE_ID"] = default_workspace_id_override

    # Any unprovided fields will be read from config file
    return Settings(**fields_overrides)


def write_settings(settings: Settings):
    """
    Write settings to config file. Reset cache of ``get_settings()``
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "SERVER_URL": settings.SERVER_URL,
        "PAT": settings.PAT.get_secret_value(),
        "DEFAULT_WORKSPACE_ID": settings.DEFAULT_WORKSPACE_ID,
    }

    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(data, f)

    # clear old cache
    get_settings.cache_clear()
