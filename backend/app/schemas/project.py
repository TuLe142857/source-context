from pydantic import BaseModel, ConfigDict, Field

from app.domain.source_file import SourceLanguage


class ProjectCreateRequest(BaseModel):
    root_dir: str = Field(
        ...,
        description="Relative sub-folder path inside the branch repository, e.g. '.' or 'backend/'",
    )
    language: SourceLanguage = Field(
        ...,
        description="Primary language of the sub-project, e.g. 'python', 'typescript'",
    )


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_dir: str | None = None
    language: SourceLanguage | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    workspace_id: int | None = None
    root_dir: str
    language: SourceLanguage
