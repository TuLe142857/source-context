"""Sub-repository profile API schema."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SubrepoProfileResponse(BaseModel):
    """Schema representing an extracted technical profile of a sub-project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_profile_id: int
    project_id: int | None = None
    name: str
    root_dir: str
    language: str
    project_type: str
    frameworks: list[str] = Field(default_factory=list)
    tech_stack: dict[str, Any] = Field(default_factory=dict)
    key_entrypoints: list[str] = Field(default_factory=list)
    directory_map: dict[str, str] = Field(default_factory=dict)
    extra_info: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
