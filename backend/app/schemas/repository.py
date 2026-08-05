"""Repository API schemas module."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.repository import (
    GitRepositoryMetadata,
    PreparedRepository,
    RepositoryAcquisitionStatus,
    RepositoryScanResult,
    RepositoryScanStatistics,
    RepositorySnapshot,
    RepositorySourceType,
)
from app.schemas.branch import BranchCreateRequest, BranchResponse
from app.schemas.workspace import MemberResponse


class InspectGitHubBranchesRequest(BaseModel):
    """Schema for requesting remote branches from a GitHub repository URL."""

    git_url: str = Field(
        ...,
        description="GitHub Repository URL, e.g. 'https://github.com/owner/repo.git'",
    )


class RemoteBranchesResponse(BaseModel):
    """Schema for returning available remote branches from GitHub."""

    git_url: str
    owner: str
    repo_name: str
    branches: list[str]


class RepositoryCreateRequest(BaseModel):
    """Schema for creating a repository under a workspace and registering selected branches."""
    git_url: str = Field(..., description="Git repository URL")
    branches: list[BranchCreateRequest] = Field(
        default_factory=list,
        description="List of selected branches to register under this repository",
    )


class SimpleRepositoryResponse(BaseModel):
    """Simple schema for returning basic repository information without relational fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    git_url: str


class RepositoryResponse(BaseModel):
    """Schema for returning repository information and its branches."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    git_url: str
    branches: list[BranchResponse] = Field(default_factory=list)


class WorkspaceHierarchyResponse(BaseModel):
    """Full hierarchy tree representation: Workspace -> Repositories -> Branches -> Projects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_name: str
    owner_id: int
    members: list[MemberResponse] = Field(default_factory=list)
    repositories: list[RepositoryResponse] = Field(default_factory=list)


__all__ = [
    "GitRepositoryMetadata",
    "InspectGitHubBranchesRequest",
    "MemberResponse",
    "PreparedRepository",
    "RemoteBranchesResponse",
    "RepositoryAcquisitionStatus",
    "RepositoryCreateRequest",
    "RepositoryResponse",
    "RepositoryScanResult",
    "RepositoryScanStatistics",
    "RepositorySnapshot",
    "RepositorySourceType",
    "SimpleRepositoryResponse",
    "WorkspaceHierarchyResponse",
]
