"""Authentication and Token Management API routes."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
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

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and return JWT access token",
)
async def register_user(
    payload: UserRegisterRequest,
    db: DBSession,
) -> TokenResponse:
    """Registers a new user and returns a signed JWT access token.

    Args:
        payload (UserRegisterRequest): User registration details.
        db (DBSession): Database session.

    Returns:
        TokenResponse: Access token and registered user object.
    """
    # Check if email or username already exists
    existing = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email or username already exists.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=user.id, expires_delta=expires_delta)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user and return JWT access token",
)
async def login_user(
    payload: UserLoginRequest,
    db: DBSession,
) -> TokenResponse:
    """Authenticates user credentials and returns a signed JWT access token.

    Args:
        payload (UserLoginRequest): Login credentials (username/email & password).
        db (DBSession): Database session.

    Returns:
        TokenResponse: Access token and authenticated user details.
    """
    result = await db.execute(
        select(User).where(
            (User.username == payload.username_or_email)
            | (User.email == payload.username_or_email)
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_active not in ("active", "true", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=user.id, expires_delta=expires_delta)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get profile of currently authenticated user",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Returns the profile of the current authenticated user.

    Args:
        current_user (CurrentUser): Authenticated user dependency.

    Returns:
        UserResponse: User profile object.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/token",
    response_model=CustomTokenResponse,
    summary="Create a custom token with custom expiration (e.g. for MCP server authentication)",
)
async def create_custom_token(
    payload: CreateCustomTokenRequest,
    current_user: CurrentUser,
) -> CustomTokenResponse:
    """Generates a custom JWT token with custom expiration for external clients.

    Args:
        payload (CreateCustomTokenRequest): Token configuration.
        current_user (CurrentUser): Authenticated user dependency.

    Returns:
        CustomTokenResponse: Generated token string and expiration timestamp.
    """
    minutes = payload.expires_in_minutes or (60 * 24 * 30)  # Default 30 days
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
