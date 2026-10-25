"""Data models and schemas for repository and sub-repository profile extraction."""

from typing import Any
from pydantic import BaseModel, Field


class SubrepoProfileResult(BaseModel):
    """Extracted technical profile of a sub-project (sub-repo)."""

    name: str = "root"
    root_dir: str = "."
    language: str = "unknown"
    project_type: str = "unknown"
    frameworks: list[str] = Field(default_factory=list)
    tech_stack: dict[str, Any] = Field(default_factory=dict)
    key_entrypoints: list[str] = Field(default_factory=list)
    directory_map: dict[str, str] = Field(default_factory=dict)
    extra_info: dict[str, Any] = Field(default_factory=dict)


class RepoProfileResult(BaseModel):
    """Complete aggregated profile of a repository with its sub-projects."""

    repository_url: str | None = None
    branch_name: str = "main"
    commit_sha: str = "HEAD"
    primary_language: str = "unknown"
    summary: str | None = None
    readme_content: str | None = None
    license_name: str | None = None
    topics: list[str] = Field(default_factory=list)
    languages_breakdown: dict[str, float] = Field(default_factory=dict)
    subrepos: list[SubrepoProfileResult] = Field(default_factory=list)
    extra_info: dict[str, Any] = Field(default_factory=dict)
