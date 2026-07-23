"""Pydantic schemas for Project API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.member import MemberResponse
from app.schemas.repository import RepositoryLinkResponse


class ProjectBase(BaseModel):
    """Base schema for Project data."""

    project_name: str
    description: str | None = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new Project."""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating an existing Project."""

    project_name: str | None = None
    description: str | None = None


class ProjectResponse(ProjectBase):
    """Schema for returning basic Project information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    """Schema for returning detailed Project information including members and repositories."""

    members: list[MemberResponse]
    repositories: list[RepositoryLinkResponse]
