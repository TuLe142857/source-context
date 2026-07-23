"""Pydantic schemas for authentication and authorization."""

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    username: str
    password: str
    full_name: str | None = None


class UserLoginRequest(BaseModel):
    """Schema for user login request."""

    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    """Schema for returning JWT token and user info after login/registration."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class CreateCustomTokenRequest(BaseModel):
    """Schema for requesting a custom expiration token (e.g., for MCP server)."""

    expires_in_minutes: int | None = 60 * 24 * 30  # Default 30 days
    token_name: str | None = "mcp_client_token"


class CustomTokenResponse(BaseModel):
    """Schema for returning a custom token response."""

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    token_name: str | None = None
