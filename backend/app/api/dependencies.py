"""Shared FastAPI dependencies."""

from typing import cast

from fastapi import Request

from app.core.config import Settings

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pat import hash_pat_token
from app.core.postgres import database
from app.core.security import decode_access_token
from app.domain.pat import PersonalAccessToken
from app.domain.user import User

security_bearer = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    """Return settings associated with the current application instance."""

    return cast(Settings, request.app.state.settings)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides an asynchronous database session for FastAPI dependencies.

    Yields:
        AsyncGenerator[AsyncSession, None]: The async database session.
    """
    async with database.async_session_factory() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]
AuthCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(security_bearer)
]


async def get_current_user(
    db: DBSession,
    credentials: AuthCredentials,
) -> User:
    """Authenticates current user via JWT Bearer Token or Personal Access Token (PAT).

    Args:
        db (AsyncSession): Database session.
        credentials (HTTPAuthorizationCredentials | None): Bearer token credentials.

    Returns:
        User: Authenticated User instance.

    Raises:
        HTTPException: If credentials missing, token invalid/expired, or user inactive.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Case A: Personal Access Token (PAT) authentication (e.g. sc_live_...)
    if token.startswith("sc_live_"):
        hashed_key = hash_pat_token(token)
        result = await db.execute(
            select(PersonalAccessToken, User)
            .join(User, PersonalAccessToken.user_id == User.id)
            .where(
                PersonalAccessToken.hashed_token == hashed_key,
                PersonalAccessToken.is_revoked.is_(False),
            )
        )
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked Personal Access Token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        pat: PersonalAccessToken = row[0]
        user_model: User = row[1]

        now = datetime.now(UTC)
        if pat.expires_at is not None and pat.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Personal Access Token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user_model.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account.",
            )

        # Update last used timestamp for the PAT token
        pat.last_used_at = now
        await db.commit()

        return user_model

    # Case B: Standard JWT Bearer token authentication
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject in token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_result = await db.execute(select(User).where(User.id == user_id))
    user_obj = user_result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )

    return user_obj


CurrentUser = Annotated[User, Depends(get_current_user)]
