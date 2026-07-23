"""Pydantic schemas for Member API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from app.enums.member_role import MemberRole


class MemberInviteRequest(BaseModel):
    """Schema for inviting a member by email."""

    email: EmailStr
    role: MemberRole = MemberRole.VIEWER


class MemberResponse(BaseModel):
    """Schema for returning member information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: MemberRole
    user_email: str
    user_username: str
    user_full_name: str | None = None
    created_at: datetime
