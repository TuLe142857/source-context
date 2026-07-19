"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime settings for the Source Context backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SOURCE_CONTEXT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Source Context Backend"
    app_version: str = "0.1.0"
    environment: Environment = "development"
    debug: bool = False
    log_level: LogLevel = "INFO"
    api_v1_prefix: str = "/api/v1"

    repository_workspace_root: Path = Path("workspace-repositories")

    scanner_max_file_size_bytes: int = Field(
        default=1_000_000,
        gt=0,
    )

    git_command_timeout_seconds: int = Field(
        default=120,
        gt=0,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()
