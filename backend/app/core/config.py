"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
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

    # General App Settings
    app_name: str = "Source Context Backend"
    app_version: str = "0.1.0"
    environment: Environment = "development"
    debug: bool = False
    log_level: LogLevel = "INFO"
    api_v1_prefix: str = "/api/v1"

    # Repository Scanner Settings
    repository_workspace_root: Path = Path("workspace-repositories")
    scanner_max_file_size_bytes: int = Field(default=1_000_000, gt=0)
    git_command_timeout_seconds: int = Field(default=120, gt=0)

    # Database & Authentication Settings (without SOURCE_CONTEXT_ prefix)
    ENV_STATE: str = Field(default="dev", validation_alias="ENV_STATE")

    POSTGRES_HOST: str = Field(default="postgres", validation_alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="mydb_dev", validation_alias="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="myuser", validation_alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(
        default="mypassword", validation_alias="POSTGRES_PASSWORD"
    )

    REDIS_HOST: str = Field(default="redis", validation_alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, validation_alias="REDIS_PORT")
    REDIS_USER: str = Field(default="myuser", validation_alias="REDIS_USER")
    REDIS_PASSWORD: str = Field(default="mypassword", validation_alias="REDIS_PASSWORD")
    CELERY_BROKER_URL_OVERRIDE: str | None = Field(
        default=None, validation_alias="CELERY_BROKER_URL"
    )

    SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        validation_alias="SECRET_KEY",
    )
    ALGORITHM: str = Field(default="HS256", validation_alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Returns synchronous PostgreSQL connection URL."""
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Returns asynchronous PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def CELERY_BROKER_URL(self) -> str:
        """Returns Celery Redis broker connection URL."""
        if self.CELERY_BROKER_URL_OVERRIDE:
            return self.CELERY_BROKER_URL_OVERRIDE
        if self.REDIS_USER:
            return f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


settings: Settings = get_settings()
