from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies import DBSession
from app.core import AppException, ErrorCode
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.model.user import User
from app.schemas.auth import (
    CreateCustomTokenRequest,
    CustomTokenResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.schemas.user import UserResponse


class AuthService:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    async def register_user(self, payload: UserRegisterRequest) -> TokenResponse:
        existing = await self.session.execute(
            select(User).where(
                (User.email == payload.email) | (User.username == payload.username)
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="A user with this email or username already exists.",
            )

        user = User(
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(subject=user.id, expires_delta=expires_delta)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            user=UserResponse.model_validate(user),
        )

    async def login_user(self, payload: UserLoginRequest) -> TokenResponse:
        result = await self.session.execute(
            select(User).where(
                (User.username == payload.username_or_email)
                | (User.email == payload.username_or_email)
            )
        )
        user = result.scalar_one_or_none()

        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AppException(
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Incorrect username/email or password.",
            )

        if user.is_active not in ("active", "true", True):
            raise AppException(
                error_code=ErrorCode.USER_INACTIVE,
                message="Inactive user account.",
            )

        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(subject=user.id, expires_delta=expires_delta)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            user=UserResponse.model_validate(user),
        )

    async def get_me(self, current_user: User) -> UserResponse:
        return UserResponse.model_validate(current_user)

    async def create_custom_token(
        self, current_user: User, payload: CreateCustomTokenRequest
    ) -> CustomTokenResponse:
        minutes = payload.expires_in_minutes or (60 * 24 * 30)
        expires_delta = timedelta(minutes=minutes)
        expire_time = datetime.now(UTC) + expires_delta

        extra_claims = {
            "token_name": payload.token_name or "mcp_client_token",
            "scope": "mcp_access",
        }
        token = create_access_token(
            subject=current_user.id,
            expires_delta=expires_delta,
            extra_claims=extra_claims,
        )

        return CustomTokenResponse(
            access_token=token,
            token_type="bearer",
            expires_at=expire_time,
            token_name=payload.token_name or "mcp_client_token",
        )


def get_auth_service(session: DBSession) -> AuthService:
    return AuthService(session=session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
