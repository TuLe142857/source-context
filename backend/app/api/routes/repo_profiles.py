"""Repository profile API routes."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DBSession
from app.core import APIResponse, ErrorCode, ResponseSuccessSchema, build_error_docs
from app.schemas.repo_profile import (
    RepoProfileExtractRequest,
    RepoProfileResponse,
)
from app.services.repo_profile_service import RepoProfileDatabaseService

router = APIRouter(prefix="/repositories", tags=["Repository Profile"])


@router.get(
    "/{repository_id}/profile",
    response_model=ResponseSuccessSchema[RepoProfileResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get or automatically extract repository profile via GitHub API",
)
async def get_repository_profile(
    repository_id: int,
    session: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    """Retrieves technical profile for a repository, extracting via GitHub API if not yet profiled."""
    service = RepoProfileDatabaseService()
    profile = await service.get_profile(session, repository_id)
    if profile is None:
        profile = await service.extract_and_save_profile(
            db=session,
            repository_id=repository_id,
            force_refresh=False,
        )

    return APIResponse.ok(data=RepoProfileResponse.model_validate(profile))


@router.post(
    "/{repository_id}/profile/extract",
    response_model=ResponseSuccessSchema[RepoProfileResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Trigger Zero-Clone API profile extraction for a repository",
)
async def extract_repository_profile(
    repository_id: int,
    payload: RepoProfileExtractRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    """Extracts or re-extracts repository profile via GitHub API and saves to database."""
    service = RepoProfileDatabaseService()
    profile = await service.extract_and_save_profile(
        db=session,
        repository_id=repository_id,
        branch_name=payload.branch_name,
        force_refresh=payload.force_refresh,
    )
    return APIResponse.ok(data=RepoProfileResponse.model_validate(profile))
