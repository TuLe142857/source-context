"""Pydantic schemas for Project (SCIP Target) configuration."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.source_file import SourceLanguage


class ProjectCreateRequest(BaseModel):
    """Schema for configuring a sub-project under a branch."""

    root_dir: str = Field(
        ...,
        description="Relative sub-folder path inside the branch repository, e.g. '.' or 'backend/'",
    )
    language: SourceLanguage = Field(
        ...,
        description="Primary language of the sub-project, e.g. 'python', 'typescript'",
    )


class ProjectResponse(BaseModel):
    """Schema for returning configured sub-project details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    root_dir: str
    language: SourceLanguage
