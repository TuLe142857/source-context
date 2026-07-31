from datetime import datetime

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
