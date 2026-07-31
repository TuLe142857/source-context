"""Pydantic schemas for Branch management and responses."""

from pydantic import BaseModel, ConfigDict, Field

from app.enums import BranchIndexingStatus
from app.schemas.project import ProjectResponse


class BranchCreateRequest(BaseModel):
    """Schema for registering a branch under a repository."""

    branch_name: str = Field(
        ..., description="Name of the Git branch, e.g. 'main', 'develop'"
    )
    commit_hashed: str = Field(default="HEAD", description="Commit hash SHA or HEAD")


class SimpleBranchResponse(BaseModel):
    """Simple schema for returning branch information without sub-projects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    branch_name: str
    commit_hashed: str
    indexing_status: BranchIndexingStatus = BranchIndexingStatus.UNINDEXED
    local_path: str | None = None


class BranchResponse(BaseModel):
    """Schema for returning branch information and its configured projects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    branch_name: str
    commit_hashed: str
    indexing_status: BranchIndexingStatus = BranchIndexingStatus.UNINDEXED
    local_path: str | None = None
    projects: list[ProjectResponse] = Field(default_factory=list)
