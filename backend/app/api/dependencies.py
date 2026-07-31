"""Shared FastAPI dependencies."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import AppException, ErrorCode
from app.core.config import Settings
from app.core.pat import hash_pat_token
from app.core.postgres import database
from app.core.qdrant import get_qdrant_client
from app.core.security import decode_access_token
from app.model.pat import PAT
from app.model.user import User
from app.retrieval.retriever import CodeRetriever
from app.services.vector_service import VectorService

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


def get_vector_retriever(
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> CodeRetriever:
    return CodeRetriever(client=qdrant_client)


DBSession = Annotated[AsyncSession, Depends(get_db)]

AuthCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(security_bearer)
]

CodeRetrieverDep = Annotated[CodeRetriever, Depends(get_vector_retriever)]


def get_vector_service(
    code_retriever: CodeRetrieverDep,
    db: DBSession,
) -> VectorService:
    return VectorService(retriever=code_retriever, db_session=db)


VectorServiceDep = Annotated[VectorService, Depends(get_vector_service)]


class CurrentUserProvider:
    type AUTH_METHOD = Literal["jwt", "pat"]

    def __init__(
        self,
        auth_methods: list[AUTH_METHOD] | tuple[AUTH_METHOD] = ("jwt",),
        required_not_none: bool = True,
    ) -> None:
        self.auth_methods = auth_methods
        self.required_not_none = required_not_none

    async def get_current_user_by_pat(
        self, db: AsyncSession, token: str
    ) -> User | None:
        if not token.startswith("sc_live_"):
            return None

        hashed_key = hash_pat_token(token)
        result = await db.execute(
            select(PAT, User)
            .join(User, PAT.user_id == User.id)
            .where(
                PAT.hashed_token == hashed_key,
                PAT.is_revoked.is_(False),
            )
        )
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked Personal Access Token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        pat: PAT = row[0]
        user_model: User = row[1]

        now = datetime.now(UTC)
        if pat.expires_at is not None and pat.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Personal Access Token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user_model.is_active not in ("active", "true", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account.",
            )

        # Update last used timestamp for the PAT token
        pat.last_used_at = now
        await db.commit()

        return user_model

    async def get_current_user_by_jwt(
        self, db: AsyncSession, token: str
    ) -> User | None:
        payload = decode_access_token(token)
        if payload is None:
            return None

        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        try:
            user_id = int(user_id_str)
        except ValueError:
            return None

        user_result = await db.execute(select(User).where(User.id == user_id))
        user_obj: User | None = user_result.scalar_one_or_none()

        if user_obj is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User belonging to this token no longer exists.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user_obj.is_active not in ("active", "true", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account.",
            )

        return user_obj

    async def __call__(
        self, db: DBSession, credentials: AuthCredentials
    ) -> User | None:
        user_obj: User | None = None

        if (credentials is not None) and (len(credentials.credentials) > 0):
            token = credentials.credentials

            if "pat" in self.auth_methods:
                user_obj = await self.get_current_user_by_pat(db, token)
            elif ("jwt" in self.auth_methods) and user_obj is None:
                user_obj = await self.get_current_user_by_jwt(db, token)

        if (user_obj is None) and self.required_not_none:
            raise AppException(ErrorCode.UNAUTHORIZED)

        return user_obj


CurrentAgent = Annotated[User, Depends(CurrentUserProvider(auth_methods=["pat"]))]
"""Auth with PAT For MCP"""

CurrentAgentOrNone = Annotated[
    User, Depends(CurrentUserProvider(auth_methods=["pat"], required_not_none=False))
]
"""Auth(Optional) with PAT for MCP"""

CurrentUser = Annotated[User, Depends(CurrentUserProvider(auth_methods=["jwt"]))]
"""Auth with JWT for normal user"""

CurrentUserOrNone = Annotated[
    User, Depends(CurrentUserProvider(auth_methods=["jwt"], required_not_none=False))
]
"""Auth(Optional) with JWT for normal user"""
