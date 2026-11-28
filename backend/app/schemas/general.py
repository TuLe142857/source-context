from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.subrepo_profile import SubrepoProfileResponse


class RepositoryRequest(BaseModel):
    workspace_id: int


class BranchRequest(BaseModel):
    workspace_id: int
    repository_id: int


class BranchProjectsRequest(BaseModel):
    workspace_id: int
    repo_id: int
    branch_name: str


class RepositoryOverviewRequest(BaseModel):
    """Request schema for repository overview and architecture information."""

    repository_id: int
    workspace_id: int | None = None
    include_readme: bool = False


class RepositoryOverviewResponse(BaseModel):
    """Comprehensive technical overview and architecture summary of a repository."""

    model_config = ConfigDict(from_attributes=True)

    repository_id: int
    name: str
    git_url: str
    profile_available: bool
    branch_name: str | None = None
    commit_sha: str | None = None
    primary_language: str | None = None
    summary: str | None = None
    license_name: str | None = None
    topics: list[str] = Field(default_factory=list)
    languages_breakdown: dict[str, float] = Field(default_factory=dict)
    readme_content: str | None = None
    subprojects: list[SubrepoProfileResponse] = Field(default_factory=list)
    extra_info: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: datetime | None = None
