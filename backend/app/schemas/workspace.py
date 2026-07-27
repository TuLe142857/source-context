"""Pydantic schemas for Workspace API requests and responses."""

from pydantic import BaseModel, ConfigDict, EmailStr


class WorkspaceBase(BaseModel):
    """Base schema for Workspace attributes."""

    workspace_name: str
    description: str | None = None


class WorkspaceCreate(WorkspaceBase):
    """Schema for workspace creation request."""

    pass


class WorkspaceUpdate(BaseModel):
    """Schema for workspace update request."""

    workspace_name: str | None = None
    description: str | None = None


class WorkspaceResponse(WorkspaceBase):
    """Schema for returning workspace information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int


class AddMemberRequest(BaseModel):
    """Schema for adding a member to workspace by email."""

    email: EmailStr


class MemberResponse(BaseModel):
    """Schema for returning workspace member information."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int
    user_id: int
    email: str | None = None
    username: str | None = None
