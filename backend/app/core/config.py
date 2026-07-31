"""Application configuration loaded from environment variables."""

from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def get_env_file_path() -> tuple[str, ...]:
    """Determines the appropriate .env file(s) to load based on environment variables.

    Returns:
        tuple[str, ...]: Tuple of environment file paths.
    """
    root_dir = Path(__file__).resolve().parents[3]
    env_state = (
        os.getenv("SOURCE_CONTEXT_ENV_STATE")
        or os.getenv("ENV_STATE")
        or os.getenv("ENV")
        or os.getenv("ENVIRONMENT")
        or "dev"
    ).lower()

    if env_state in ("dev", "development"):
        primary = root_dir / ".env.dev"
    elif env_state in ("prod", "production"):
        primary = root_dir / ".env"
    elif env_state in ("test", "testing"):
        primary = root_dir / ".env.test"
    else:
        primary = root_dir / f".env.{env_state}"

    files: list[str] = []
    fallback = root_dir / ".env"
    if fallback.exists():
        files.append(str(fallback))

    if primary.exists() and str(primary) not in files:
        files.append(str(primary))

    return tuple(files) if files else (".env",)


class Settings(BaseSettings):
    """Runtime settings for the Source Context backend."""

    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding="utf-8",
        env_prefix="SOURCE_CONTEXT_",
        case_sensitive=False,
        extra="ignore",
    )

    # General App Settings
    app_name: str = Field(
        default="Source Context Backend",
        validation_alias=AliasChoices("SOURCE_CONTEXT_APP_NAME", "APP_NAME"),
    )
    app_version: str = Field(
        default="0.1.0",
        validation_alias=AliasChoices("SOURCE_CONTEXT_APP_VERSION", "APP_VERSION"),
    )
    environment: Environment = Field(
        default="development",
        validation_alias=AliasChoices("SOURCE_CONTEXT_ENVIRONMENT", "ENVIRONMENT"),
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("SOURCE_CONTEXT_DEBUG", "DEBUG"),
    )
    log_level: LogLevel = Field(
        default="INFO",
        validation_alias=AliasChoices("SOURCE_CONTEXT_LOG_LEVEL", "LOG_LEVEL"),
    )
    api_v1_prefix: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("SOURCE_CONTEXT_API_V1_PREFIX", "API_V1_PREFIX"),
    )

    # Repository Scanner Settings
    repository_workspace_root: Path = Field(
        default=Path("/workspace-repositories"),
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_REPOSITORY_WORKSPACE_ROOT", "REPOSITORY_WORKSPACE_ROOT"
        ),
    )
    scanner_max_file_size_bytes: int = Field(
        default=1_000_000,
        gt=0,
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_SCANNER_MAX_FILE_SIZE_BYTES", "SCANNER_MAX_FILE_SIZE_BYTES"
        ),
    )
    git_command_timeout_seconds: int = Field(
        default=120,
        gt=0,
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_GIT_COMMAND_TIMEOUT_SECONDS", "GIT_COMMAND_TIMEOUT_SECONDS"
        ),
    )

    # Environment State
    ENV_STATE: str = Field(
        default="dev",
        validation_alias=AliasChoices("SOURCE_CONTEXT_ENV_STATE", "ENV_STATE"),
    )

    # Database Settings
    POSTGRES_HOST: str = Field(
        default="postgres",
        validation_alias=AliasChoices("SOURCE_CONTEXT_POSTGRES_HOST", "POSTGRES_HOST"),
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices("SOURCE_CONTEXT_POSTGRES_PORT", "POSTGRES_PORT"),
    )
    POSTGRES_DB: str = Field(
        default="mydb_dev",
        validation_alias=AliasChoices("SOURCE_CONTEXT_POSTGRES_DB", "POSTGRES_DB"),
    )
    POSTGRES_USER: str = Field(
        default="myuser",
        validation_alias=AliasChoices("SOURCE_CONTEXT_POSTGRES_USER", "POSTGRES_USER"),
    )
    POSTGRES_PASSWORD: str = Field(
        default="mypassword",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_POSTGRES_PASSWORD", "POSTGRES_PASSWORD"
        ),
    )

    # Redis Settings
    REDIS_HOST: str = Field(
        default="redis",
        validation_alias=AliasChoices("SOURCE_CONTEXT_REDIS_HOST", "REDIS_HOST"),
    )
    REDIS_PORT: int = Field(
        default=6379,
        validation_alias=AliasChoices("SOURCE_CONTEXT_REDIS_PORT", "REDIS_PORT"),
    )
    REDIS_USER: str = Field(
        default="myuser",
        validation_alias=AliasChoices("SOURCE_CONTEXT_REDIS_USER", "REDIS_USER"),
    )
    REDIS_PASSWORD: str = Field(
        default="mypassword",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_REDIS_PASSWORD", "REDIS_PASSWORD"
        ),
    )
    CELERY_BROKER_URL_OVERRIDE: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_CELERY_BROKER_URL", "CELERY_BROKER_URL"
        ),
    )

    # Security Settings
    SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        validation_alias=AliasChoices("SOURCE_CONTEXT_SECRET_KEY", "SECRET_KEY"),
    )
    ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("SOURCE_CONTEXT_ALGORITHM", "ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24,
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_ACCESS_TOKEN_EXPIRE_MINUTES", "ACCESS_TOKEN_EXPIRE_MINUTES"
        ),
    )

    # NEO4J CONFIG
    NEO4J_USER: str = Field(
        default="neo4j",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_NEO4J_USER",
            "SOURCE_CONTEXT_NEO4J_USERNAME",
            "NEO4J_USER",
            "NEO4J_USERNAME",
        ),
    )
    NEO4J_PASSWORD: SecretStr = Field(
        default=SecretStr("neo4jpassword"),
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_NEO4J_PASSWORD", "NEO4J_PASSWORD"
        ),
    )
    NEO4J_PORT: int = Field(
        default=7687,
        validation_alias=AliasChoices("SOURCE_CONTEXT_NEO4J_PORT", "NEO4J_PORT"),
    )
    NEO4J_HOST: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("SOURCE_CONTEXT_NEO4J_HOST", "NEO4J_HOST"),
    )

    # Qdrant Vector DB
    QDRANT_HOST: str = Field(
        default="qdrant",
        validation_alias=AliasChoices("SOURCE_CONTEXT_QDRANT_HOST", "QDRANT_HOST"),
    )
    QDRANT_PORT: int = Field(
        default=6333,
        validation_alias=AliasChoices("SOURCE_CONTEXT_QDRANT_PORT", "QDRANT_PORT"),
    )
    QDRANT_GRPC_PORT: int = Field(
        default=6334,
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_QDRANT_GRPC_PORT", "QDRANT_GRPC_PORT"
        ),
    )
    QDRANT_API_KEY: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_QDRANT_API_KEY", "QDRANT_API_KEY"
        ),
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="code_chunks",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_QDRANT_COLLECTION_NAME", "QDRANT_COLLECTION_NAME"
        ),
    )

    # OpenAI Settings
    OPENAI_API_KEY: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_OPENAI_API_KEY", "OPENAI_API_KEY"
        ),
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("SOURCE_CONTEXT_OPENAI_MODEL", "OPENAI_MODEL"),
    )

    # Voyage AI Settings
    VOYAGE_API_KEY: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_VOYAGE_API_KEY", "VOYAGE_API_KEY"
        ),
    )
    VOYAGE_EMBEDDING_MODEL: str = Field(
        default="voyage-code-3",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_VOYAGE_EMBEDDING_MODEL", "VOYAGE_EMBEDDING_MODEL"
        ),
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
    def NEO4J_URI(self) -> str:
        """Neo4j URI for neomodel, not neo4j driver.

        Format: bolt://[user]:[password]@[host]:[bolt_port]
        """
        return (
            f"bolt://{self.NEO4J_USER}:{self.NEO4J_PASSWORD.get_secret_value()}@"
            f"{self.NEO4J_HOST}:{self.NEO4J_PORT}"
        )

    # S3 Setting
    S3_DEFAULT_BUCKET: str = Field(
        default="default",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_S3_DEFAULT_BUCKET", "S3_DEFAULT_BUCKET"
        ),
    )
    S3_ENDPOINT: str = Field(
        default="http://minio:9000",
        validation_alias=AliasChoices("SOURCE_CONTEXT_S3_ENDPOINT", "S3_ENDPOINT"),
    )
    S3_ACCESS_KEY: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_MINIO_ROOT_USER", "MINIO_ROOT_USER", "S3_ACCESS_KEY"
        ),
    )
    S3_SECRET_KEY: SecretStr = Field(
        default=SecretStr("minioadmin"),
        validation_alias=AliasChoices(
            "SOURCE_CONTEXT_MINIO_ROOT_PASSWORD", "MINIO_ROOT_PASSWORD", "S3_SECRET_KEY"
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def CELERY_BROKER_URL(self) -> str:
        """Returns Celery Redis broker connection URL."""
        if self.CELERY_BROKER_URL_OVERRIDE:
            return self.CELERY_BROKER_URL_OVERRIDE
        if self.REDIS_USER:
            return (
                f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@"
                f"{self.REDIS_HOST}:{self.REDIS_PORT}/0"
            )
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


settings: Settings = get_settings()
