from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core import AppException, ErrorCode
from app.core.pat import generate_raw_pat_token
from app.model.pat import PAT
from app.schemas.pat import PATCreateResponse, PATResponse


class PatService:
    def __init__(self, session: DBSession, current_user: CurrentUser) -> None:
        self.session = session
        self.current_user = current_user

    async def create_token(
        self, name: str, expires_in_days: int | None = 365
    ) -> PATCreateResponse:
        raw_token, token_prefix, hashed_token = generate_raw_pat_token()

        expired_at = None
        if expires_in_days is not None:
            expired_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        pat = PAT(
            user_id=self.current_user.id,
            name=name,
            token_prefix=token_prefix,
            hashed_token=hashed_token,
            expired_at=expired_at,
        )
        self.session.add(pat)
        await self.session.commit()
        await self.session.refresh(pat)

        return PATCreateResponse(
            id=pat.id,
            name=pat.name,
            raw_token=raw_token,
            token_prefix=pat.token_prefix,
            expired_at=pat.expired_at,
            expires_at=pat.expired_at,
        )

    async def get_user_tokens(self) -> list[PATResponse]:
        stmt = select(PAT).where(
            PAT.user_id == self.current_user.id,
            PAT.is_revoked.is_(False),
        )
        results = await self.session.scalars(stmt)
        pats = list(results.all())
        return [PATResponse.model_validate(p) for p in pats]

    async def revoke_token(self, token_id: int) -> None:
        stmt = select(PAT).where(
            PAT.id == token_id,
            PAT.user_id == self.current_user.id,
        )
        result = await self.session.scalars(stmt)
        pat = result.one_or_none()

        if pat is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Personal Access Token not found",
            )

        pat.is_revoked = True
        await self.session.commit()


def get_pat_service(current_user: CurrentUser, session: DBSession) -> PatService:
    return PatService(session=session, current_user=current_user)


PatServiceDep = Annotated[PatService, Depends(get_pat_service)]
