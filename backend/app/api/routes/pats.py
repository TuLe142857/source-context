"""API routes for Personal Access Token (PAT) / API Key management."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core.pat import generate_raw_pat_token
from app.model.pat import PAT
from app.schemas.pat import PATCreateRequest, PATCreateResponse, PATResponse

router = APIRouter(prefix="/user/tokens", tags=["Personal Access Tokens (API Keys)"])


@router.post(
    "",
    response_model=PATCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Personal Access Token (API Key)",
)
@router.post(
    "/",
    response_model=PATCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Personal Access Token (API Key)",
)
async def create_personal_access_token(
    payload: PATCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> PATCreateResponse:
    """Generates a new Personal Access Token (PAT) for external clients (e.g. MCP CLI).

    Args:
        payload (PATCreateRequest): Token creation parameters (name, expires_in_days).
        current_user (CurrentUser): Currently authenticated user.
        db (DBSession): Database session.

    Returns:
        PATCreateResponse: Created token object with raw_token secret (shown ONLY ONCE).
    """
    raw_token, token_prefix, hashed_token = generate_raw_pat_token()

    expired_at = None
    if payload.expires_in_days is not None:
        expired_at = datetime.now(UTC) + timedelta(days=payload.expires_in_days)

    pat = PAT(
        user_id=current_user.id,
        name=payload.name,
        token_prefix=token_prefix,
        hashed_token=hashed_token,
        expired_at=expired_at,
    )
    db.add(pat)
    await db.commit()
    await db.refresh(pat)

    return PATCreateResponse(
        id=pat.id,
        name=pat.name,
        raw_token=raw_token,
        token_prefix=pat.token_prefix,
        expires_at=pat.expired_at,
        created_at=datetime.now(UTC),
    )


@router.get(
    "",
    response_model=list[PATResponse],
    summary="List all Personal Access Tokens for current user",
)
@router.get(
    "/",
    response_model=list[PATResponse],
    summary="List all Personal Access Tokens for current user",
)
async def list_personal_access_tokens(
    current_user: CurrentUser,
    db: DBSession,
) -> list[PATResponse]:
    """Retrieves all active Personal Access Tokens created by the user.

    Args:
        current_user (CurrentUser): Currently authenticated user.
        db (DBSession): Database session.

    Returns:
        list[PATResponse]: List of token metadata objects.
    """
    result = await db.execute(
        select(PAT).where(
            PAT.user_id == current_user.id,
            PAT.is_revoked.is_(False),
        )
    )
    pats = result.scalars().all()
    return [PATResponse.model_validate(p) for p in pats]


@router.delete(
    "/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke/Delete a Personal Access Token",
)
async def revoke_personal_access_token(
    token_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Revokes a Personal Access Token so it can no longer be used for authentication.

    Args:
        token_id (int): ID of the token to revoke.
        current_user (CurrentUser): Currently authenticated user.
        db (DBSession): Database session.

    Raises:
        HTTPException: If token is not found or does not belong to user.
    """
    result = await db.execute(
        select(PAT).where(
            PAT.id == token_id,
            PAT.user_id == current_user.id,
        )
    )
    pat = result.scalar_one_or_none()

    if pat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal Access Token not found.",
        )

    pat.is_revoked = True
    await db.commit()
