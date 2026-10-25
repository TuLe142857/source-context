"""Repository profile API schemas."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.subrepo_profile import SubrepoProfileResponse


class RepoProfileResponse(BaseModel):
    """Schema representing high-level repository profile with nested sub-projects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    branch_id: int | None = None
    branch_name: str
    commit_sha: str
    primary_language: str
    summary: str | None = None
    readme_content: str | None = None
    license_name: str | None = None
    topics: list[str] = Field(default_factory=list)
    languages_breakdown: dict[str, float] = Field(default_factory=dict)
    extra_info: dict[str, Any] = Field(default_factory=dict)
    subrepo_profiles: list[SubrepoProfileResponse] = Field(default_factory=list)
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
