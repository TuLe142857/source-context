"""GitHub App webhook and OAuth installation callback routes."""

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.core import (
    APIResponse,
    AppException,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.core.config import settings
from app.schemas.webhook import GitHubStatusResponse, GitHubWebhookResponse
from app.services.github_app_service import GitHubAppService, GitHubAppServiceDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_signature(request: Request) -> bool:
    """Verifies that the webhook request is signed with the correct secret.

    Maintained for backward compatibility and test suites.

    Args:
        request (Request): The incoming FastAPI request.

    Returns:
        bool: True if signature is valid, False otherwise.
    """
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.body()
    return GitHubAppService.verify_signature(payload, signature)


async def _resolve_state_to_user_and_workspace(
    db: AsyncSession, state: str | None
) -> tuple[int | None, int | None]:
    """Parses state string to resolve user_id and workspace_id.

    Maintained for backward compatibility and test suites.

    Args:
        db (AsyncSession): Database session.
        state (str | None): The state query param passed during installation.

    Returns:
        tuple[int | None, int | None]: Resolved (user_id, workspace_id).
    """
    service = GitHubAppService(session=db)
    return await service.resolve_state_to_user_and_workspace(state)


@router.post(
    "/github",
    response_model=ResponseSuccessSchema[GitHubWebhookResponse],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Handle incoming GitHub App webhooks",
)
async def github_webhook(
    request: Request,
    service: GitHubAppServiceDep,
) -> APIResponse:
    """GitHub App webhook endpoint for handling repository installations and additions.

    Args:
        request (Request): The incoming webhook request.
        service (GitHubAppServiceDep): Injected GitHub App service.

    Returns:
        APIResponse: Standard API response containing GitHubWebhookResponse.

    Raises:
        AppException: If signature verification fails when secret is configured.
    """
    if settings.GITHUB_WEBHOOK_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        payload_bytes = await request.body()
        if not service.verify_signature(payload_bytes, signature):
            logger.warning("GitHub webhook signature verification failed")
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Invalid webhook signature",
            )
    else:
        payload_bytes = await request.body()

    event = request.headers.get("X-GitHub-Event")
    payload: dict[str, Any] = await request.json() if payload_bytes else {}

    result = await service.handle_webhook(event=event, payload=payload)
    return APIResponse.ok(data=result)


@router.get(
    "/callback",
    responses=build_error_docs(
        ErrorCode.BAD_REQUEST,
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="GitHub App OAuth installation callback redirect",
)
async def github_callback(
    service: GitHubAppServiceDep,
    code: str | None = None,
    installation_id: int | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Redirect callback endpoint for GitHub App installation completion.

    Args:
        service (GitHubAppServiceDep): Injected GitHub App service.
        code (str | None, optional): Optional OAuth code from GitHub. Defaults to None.
        installation_id (int | None, optional): The GitHub installation ID. Defaults to None.
        state (str | None, optional): State parameter passing user_id and workspace_id. Defaults to None.

    Returns:
        RedirectResponse: Redirect to the frontend workspace or workspace list page.
    """
    redirect_url = await service.complete_installation(
        installation_id=installation_id, state=state
    )
    return RedirectResponse(url=redirect_url)


@router.get(
    "/setup",
    responses=build_error_docs(
        ErrorCode.BAD_REQUEST,
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="GitHub App post-installation setup redirect",
)
async def github_setup(
    service: GitHubAppServiceDep,
    installation_id: int | None = None,
    setup_action: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Redirect setup endpoint for GitHub App installation completion.

    Args:
        service (GitHubAppServiceDep): Injected GitHub App service.
        installation_id (int | None, optional): The GitHub installation ID. Defaults to None.
        setup_action (str | None, optional): The action performed. Defaults to None.
        state (str | None, optional): State parameter passing user_id and workspace_id. Defaults to None.

    Returns:
        RedirectResponse: Redirect to the frontend workspace or workspace list page.
    """
    redirect_url = await service.complete_installation(
        installation_id=installation_id, state=state
    )
    return RedirectResponse(url=redirect_url)


@router.get(
    "/status",
    response_model=ResponseSuccessSchema[GitHubStatusResponse],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get GitHub App connection status for current user",
)
async def get_github_status(
    current_user: CurrentUser,
    service: GitHubAppServiceDep,
) -> APIResponse:
    """Retrieves GitHub App installation status for the authenticated user.

    Args:
        current_user (CurrentUser): The currently authenticated user.
        service (GitHubAppServiceDep): Injected GitHub App service.

    Returns:
        APIResponse: Standard API response with GitHubStatusResponse data.
    """
    data = service.get_status(current_user)
    return APIResponse.ok(data=data)


@router.delete(
    "/unlink",
    response_model=ResponseSuccessSchema[GitHubStatusResponse],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Unlink GitHub App installation from current user account",
)
async def unlink_github(
    current_user: CurrentUser,
    service: GitHubAppServiceDep,
) -> APIResponse:
    """Unlinks the GitHub App installation from the authenticated user's account.

    Args:
        current_user (CurrentUser): The currently authenticated user.
        service (GitHubAppServiceDep): Injected GitHub App service.

    Returns:
        APIResponse: Updated GitHub connection status.
    """
    data = await service.unlink_installation(current_user)
    return APIResponse.ok(
        message="GitHub App unlinked successfully.",
        data=data,
    )
