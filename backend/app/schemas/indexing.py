"""Pydantic schemas for Indexing Job status and trigger requests."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IndexingJobResponse(BaseModel):
    """Schema for returning IndexingJob status information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    branch_id: int
    status: str
    progress_pct: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
