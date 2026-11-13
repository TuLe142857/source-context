from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TriggerBranchIndexingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit_hashed: str | None = None


class IndexingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    branch_id: int
    status: str
    progress_pct: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class IndexingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    branch_id: int
    job_id: int | None
    base_commit_sha: str | None
    target_commit_sha: str
    mode: str
    status: str
    current_stage: str | None
    fallback_reason: str | None
    error_message: str | None
    statistics: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class IndexingStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: int
    branch_id: int
    latest_observed_commit_sha: str | None
    indexed_commit_sha: str | None
    index_version: str | None
    checkpoint_valid: bool
    status: str
    updated_at: datetime
