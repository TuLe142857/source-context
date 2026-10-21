"""Repository profile API schemas."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class RepoProfileResponse(BaseModel):
    """Schema representing an extracted technical profile of a repository."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    branch_id: int | None = None
    branch_name: str
    commit_sha: str
    primary_language: str
    project_type: str
    summary: str | None = None
    tech_stack: dict[str, Any] = Field(default_factory=dict)
    dev_commands: dict[str, Any] = Field(default_factory=dict)
    coding_conventions: dict[str, Any] = Field(default_factory=dict)
    key_entrypoints: list[str] = Field(default_factory=list)
    directory_map: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    extra_info: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: datetime


class RepoProfileExtractRequest(BaseModel):
    """Request schema to trigger API-based profile extraction."""

    branch_name: str | None = Field(
        default=None,
        description="Target branch name. Defaults to repository default branch.",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force re-analyzing even if commit SHA has not changed.",
    )
