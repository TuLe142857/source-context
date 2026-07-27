"""Pydantic schemas for User API requests and responses."""

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Base schema for User data."""

    email: EmailStr
    username: str
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new User."""

    pass


class UserResponse(UserBase):
    """Schema for returning User information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: str


class UserTestDBResponse(BaseModel):
    """Schema for returning database health and test query results."""

    status: str
    database_connected: bool
    user_count: int
    message: str
