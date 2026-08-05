from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from redis.asyncio import Redis
from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import DBSession, RedisDep
from app.core import AppException, ErrorCode
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_password,
)
from app.model.user import User
from app.schemas.auth import (
    CreateCustomTokenRequest,
    CustomTokenResponse,
    RegisterRequest,
    TokenResponse,
    UserLoginRequest,
    RegisterVerifyRequest,
)
from app.schemas.user import UserResponse
from .mail_service import MailService, MailServiceDep


REGISTER_OTP_TTL_SECONDS = 5 * 60
REGISTER_OTP_KEY_PREFIX = "otp:register:"


class AuthService:
    def __init__(
        self, session: DBSession, redis: Redis, mail_service: MailService
    ) -> None:
        self.session = session
        self.redis = redis
        self.mail_service = mail_service

    async def register_user(
        self, payload: RegisterRequest, bg_tasks: BackgroundTasks | None = None
    ) -> None:
        """

        Args:
            payload: payload contain email
            bg_tasks: BackgroundTasks instance use to send email. If None, send email in current thread

        Returns:
            None

        Raises:
            AppException:
                ErrorCode.RESOURCE_ALREADY_EXISTS: Email already registered.
        """
        existing = await self.session.execute(
            select(User).where(User.email == payload.email)
        )
        if existing.scalar_one_or_none() is not None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                message="A user with this email already exists.",
            )

        otp = generate_otp()

        await self.redis.set(
            f"{REGISTER_OTP_KEY_PREFIX}{payload.email}",
            hash_otp(otp),
            ex=REGISTER_OTP_TTL_SECONDS,
        )

        mail_send_kwargs = {
            "to": payload.email,
            "subject": "Verify your Source Context account",
            "template_name": "registration_otp",
            "context": {
                "otp_code": otp,
                "expire_minutes": REGISTER_OTP_TTL_SECONDS // 60,
            },
        }
        if bg_tasks is not None:
            bg_tasks.add_task(self.mail_service.send_template_email, **mail_send_kwargs)
        else:
            await run_in_threadpool(
                self.mail_service.send_template_email, **mail_send_kwargs
            )

    async def verify_registration_otp(
        self, payload: RegisterVerifyRequest
    ) -> TokenResponse:
        key = f"{REGISTER_OTP_KEY_PREFIX}{payload.email}"
        stored_hash = await self.redis.get(key)
        if stored_hash is None:
            raise AppException(
                error_code=ErrorCode.CODE_EXPIRED,
                message="OTP has expired or does not exist. Please register again.",
            )

        if stored_hash != hash_otp(payload.otp):
            raise AppException(
                error_code=ErrorCode.INVALID_CODE,
                message="Invalid OTP code.",
            )

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

        await self.redis.delete(key)

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


def get_auth_service(
    session: DBSession, redis: RedisDep, mail_service: MailServiceDep
) -> AuthService:
    return AuthService(session=session, redis=redis, mail_service=mail_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
