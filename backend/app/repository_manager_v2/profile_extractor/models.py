"""Data models and schemas for repository profile extraction.

This module defines standardized Pydantic data transfer objects (DTOs)
representing the extracted technical profile, dependencies, commands,
and conventions of a repository.
"""

from typing import Any
from pydantic import BaseModel, Field


class TechStackInfo(BaseModel):
    """Detailed breakdown of technologies and packages in the repository."""

    language: str = "unknown"
    runtime_version: str | None = None
    package_manager: str | None = None
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    orm: list[str] = Field(default_factory=list)
    task_queues: list[str] = Field(default_factory=list)
    linters: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)
    extra_packages: list[str] = Field(default_factory=list)


class DevCommandsInfo(BaseModel):
    """Common development, linting, and testing commands."""

    run: str | None = None
    test: str | None = None
    lint: str | None = None
    format: str | None = None
    build: str | None = None


class CodingConventionsInfo(BaseModel):
    """Coding style and convention configurations detected in the project."""

    naming: str | None = None
    strict_typing: bool | None = None
    linter: str | None = None
    formatter: str | None = None


class MetricsInfo(BaseModel):
    """Basic repository statistics and file metrics."""

    total_files: int = 0
    has_readme: bool = False
    readme_file: str | None = None
    detected_manifests: list[str] = Field(default_factory=list)


class RepoProfileResult(BaseModel):
    """Complete aggregated profile of a repository."""

    repository_url: str | None = None
    branch_name: str | None = None
    commit_sha: str | None = None
    primary_language: str = "unknown"
    project_type: str = "unknown"
    summary: str | None = None
    tech_stack: TechStackInfo = Field(default_factory=TechStackInfo)
    key_entrypoints: list[str] = Field(default_factory=list)
    directory_map: dict[str, str] = Field(default_factory=dict)
    dev_commands: DevCommandsInfo = Field(default_factory=DevCommandsInfo)
    coding_conventions: CodingConventionsInfo = Field(
        default_factory=CodingConventionsInfo
    )
    metrics: MetricsInfo = Field(default_factory=MetricsInfo)
    extra_info: dict[str, Any] = Field(default_factory=dict)
