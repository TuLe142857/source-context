from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr


class RegisterVerifyRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None
    otp: str


class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class CreateCustomTokenRequest(BaseModel):
    expires_in_minutes: int | None = 60 * 24 * 30
    token_name: str | None = "mcp_client_token"


class CustomTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    token_name: str | None = None
