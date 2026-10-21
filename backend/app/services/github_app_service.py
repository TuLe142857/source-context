"""Service for GitHub App webhooks, OAuth callbacks, and installation lifecycle."""

import hashlib
import hmac
import json
import logging
from typing import Annotated, Any
from urllib.parse import unquote

from fastapi import Depends
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBSession
from app.core.config import settings
from app.core.error_code import ErrorCode
from app.core.exceptions import AppException
from app.core.redis import get_redis_async_client
from app.enums import BranchIndexingStatus, IndexingJobStatus
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.repository import Repository
from app.model.user import User
from app.model.workspace import Workspace
from app.schemas.webhook import GitHubStatusResponse, GitHubWebhookResponse
from app.services.branch_service import BranchService
from app.tasks.indexing import index_branch_task

logger = logging.getLogger(__name__)


class GitHubAppService:
    """Service handling GitHub App webhooks, installations, and connection states."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """Initializes the GitHubAppService.

        Args:
            session (AsyncSession): Database session.
        """
        self.session = session

    @staticmethod
    def verify_signature(payload: bytes, signature: str | None) -> bool:
        """Verifies HMAC SHA256 signature against configured webhook secret.

        Args:
            payload (bytes): Raw request body.
            signature (str | None): Signature header from X-Hub-Signature-256.

        Returns:
            bool: True if signature matches, False otherwise.
        """
        if not signature or not settings.GITHUB_WEBHOOK_SECRET:
            return False
        secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
        computed = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def resolve_state_to_user_and_workspace(
        self, state: str | None
    ) -> tuple[int | None, int | None]:
        """Parses state string to resolve user_id and workspace_id.

        Supports JSON format, delimited format (user_X_ws_Y or X:Y), or simple numeric ID.

        Args:
            state (str | None): The state query param passed during installation.

        Returns:
            tuple[int | None, int | None]: Resolved (user_id, workspace_id).
        """
        if not state:
            return None, None

        decoded = unquote(state).strip()

        # 1. Try parsing JSON format: {"user_id": 1, "workspace_id": 2}
        if decoded.startswith("{") and decoded.endswith("}"):
            try:
                data = json.loads(decoded)
                user_id = data.get("user_id")
                workspace_id = data.get("workspace_id")
                return (
                    int(user_id) if user_id is not None else None,
                    int(workspace_id) if workspace_id is not None else None,
                )
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # 2. Try parsing delimited string: user_1_ws_2 or 1:2
        if ":" in decoded:
            parts = decoded.split(":")
            try:
                return int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                pass

        if "_ws_" in decoded:
            try:
                u_part, ws_part = decoded.split("_ws_")
                user_id = int(u_part.replace("user_", ""))
                workspace_id = int(ws_part)
                return user_id, workspace_id
            except (ValueError, IndexError):
                pass

        # 3. Simple integer: check whether it matches User.id or Workspace.id
        try:
            val = int(decoded)
        except ValueError:
            return None, None

        user_stmt = select(User.id).where(User.id == val)
        user_res = await self.session.execute(user_stmt)
        if user_res.scalar_one_or_none() is not None:
            return val, None

        ws_stmt = select(Workspace).where(Workspace.id == val)
        ws_res = await self.session.execute(ws_stmt)
        workspace = ws_res.scalar_one_or_none()
        if workspace is not None:
            return workspace.owner_id, workspace.id

        return val, None

    async def handle_webhook(
        self, event: str | None, payload: dict[str, Any]
    ) -> GitHubWebhookResponse:
        """Processes incoming GitHub webhook events.

        Handles push events, installation deletions, and repository attachments.

        Args:
            event (str | None): Event name from X-GitHub-Event header.
            payload (dict[str, Any]): Parsed JSON payload from webhook request.

        Returns:
            GitHubWebhookResponse: Result of webhook handling.
        """
        logger.info("Handling GitHub webhook event: %s", event)

        if event == "push":
            ref = payload.get("ref", "")
            if not ref.startswith("refs/heads/"):
                return GitHubWebhookResponse(
                    status="ignored", reason="not a branch push"
                )

            branch_name = ref[len("refs/heads/") :]
            clone_url = payload.get("repository", {}).get("clone_url")
            new_commit_hash = payload.get("after")

            if not clone_url or not new_commit_hash:
                return GitHubWebhookResponse(
                    status="ignored",
                    reason="missing repository details or commit hash",
                )

            repo_stmt = select(Repository).where(Repository.git_url == clone_url)
            repo_res = await self.session.execute(repo_stmt)
            repo_obj = repo_res.scalar_one_or_none()

            if not repo_obj:
                repo_stmt = select(Repository).where(
                    Repository.git_url == clone_url.removesuffix(".git")
                )
                repo_res = await self.session.execute(repo_stmt)
                repo_obj = repo_res.scalar_one_or_none()
                if not repo_obj:
                    return GitHubWebhookResponse(
                        status="ignored", reason="repository not found in system"
                    )

            branch_stmt = select(Branch).where(
                Branch.repository_id == repo_obj.id,
                Branch.branch_name == branch_name,
            )
            branch_res = await self.session.execute(branch_stmt)
            branches = list(branch_res.scalars().all())

            updated_count = 0
            for branch in branches:
                if branch.indexing_status == BranchIndexingStatus.INDEXED:
                    branch.indexing_status = BranchIndexingStatus.OUTDATED
                    updated_count += 1

            await self.session.commit()
            return GitHubWebhookResponse(
                status="ok", branches_updated_to_outdated=updated_count
            )

        action = payload.get("action")
        installation_id = payload.get("installation", {}).get("id")

        if not installation_id:
            logger.warning("Webhook payload missing installation.id")
            return GitHubWebhookResponse(status="ignored", reason="no installation_id")

        if event == "installation" and action == "deleted":
            user_stmt = select(User).where(
                User.github_installation_id == installation_id
            )
            user_res = await self.session.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            if user:
                user.github_installation_id = None
                user.github_username = None
                await self.session.commit()
                logger.info(
                    "Unlinked GitHub installation %s from user %s",
                    installation_id,
                    user.id,
                )
            return GitHubWebhookResponse(status="ok", message="installation unlinked")

        account = payload.get("installation", {}).get("account", {})
        gh_username = account.get("login") or payload.get("sender", {}).get("login")

        repos: list[dict[str, Any]] = []
        if event == "installation_repositories" and action == "added":
            repos = payload.get("repositories_added", [])
        elif event == "installation" and action in (
            "created",
            "added",
            "new_permissions",
        ):
            repos = payload.get("repositories", [])
        elif event == "installation_repositories" and action == "removed":
            return GitHubWebhookResponse(
                status="ok", message="repositories removed event received"
            )
        else:
            return GitHubWebhookResponse(
                status="ignored",
                reason=f"unhandled event/action: {event}/{action}",
            )

        try:
            redis_client = get_redis_async_client()
            cache_data = json.dumps({"username": gh_username, "repos": repos})
            await redis_client.setex(
                f"github_installation:{installation_id}", 3600, cache_data
            )
        except (RedisError, ConnectionError) as exc:
            logger.debug("Could not cache installation info in Redis: %s", exc)

        user_stmt = select(User).where(User.github_installation_id == installation_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            logger.info(
                "Installation %s received for pending user setup (cached account: %s)",
                installation_id,
                gh_username,
            )
            return GitHubWebhookResponse(
                status="ok",
                reason=(
                    f"installation cached; pending callback for installation_id {installation_id}"
                ),
            )

        if gh_username and user.github_username != gh_username:
            user.github_username = gh_username

        if not repos:
            await self.session.commit()
            return GitHubWebhookResponse(
                status="ok", message="user updated; no repositories to process"
            )

        ws_stmt = select(Workspace).where(Workspace.owner_id == user.id)
        ws_res = await self.session.execute(ws_stmt)
        workspaces = list(ws_res.scalars().all())

        if not workspaces:
            await self.session.commit()
            logger.info("User %s has no workspaces to attach repositories to", user.id)
            return GitHubWebhookResponse(
                status="ok",
                message="repositories associated with user; no workspaces found",
            )

        branch_service = BranchService(session=self.session)
        tracked_count = 0

        for workspace in workspaces:
            for repo in repos:
                name = repo.get("name")
                clone_url = repo.get("clone_url")
                default_branch = repo.get("default_branch", "main")

                if not name or not clone_url:
                    continue

                repo_obj = await branch_service.attach_repository_db(
                    workspace_id=workspace.id,
                    git_url=clone_url,
                    repo_name=name,
                    branch_names=[default_branch],
                    user_id=user.id,
                )

                branch_stmt = select(Branch).where(
                    Branch.repository_id == repo_obj.id,
                    Branch.branch_name == default_branch,
                )
                branch_res = await self.session.execute(branch_stmt)
                branch_obj = branch_res.scalar_one_or_none()

                if (
                    branch_obj
                    and branch_obj.indexing_status != BranchIndexingStatus.INDEXING
                ):
                    branch_obj.indexing_status = BranchIndexingStatus.INDEXING

                    job = IndexingJob(
                        workspace_id=workspace.id,
                        branch_id=branch_obj.id,
                        status=IndexingJobStatus.PENDING,
                        progress_pct=0,
                    )
                    self.session.add(job)
                    await self.session.flush()

                    index_branch_task.delay(workspace.id, branch_obj.id, job.id)
                    tracked_count += 1

        await self.session.commit()
        return GitHubWebhookResponse(status="ok", repositories_tracked=tracked_count)

    async def complete_installation(
        self,
        installation_id: int | None,
        state: str | None,
    ) -> str:
        """Handles GitHub App installation completion callback.

        Associates installation with SaaS user and triggers repository ingestion.

        Args:
            installation_id (int | None): The GitHub App installation ID.
            state (str | None): State query parameter passed to GitHub.

        Returns:
            str: Frontend redirect destination URL.

        Raises:
            AppException: If parameters are missing, invalid, or user is not found.
        """
        if not installation_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Missing installation_id",
            )

        if not state:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Missing state parameter (user_id required)",
            )

        user_id, workspace_id = await self.resolve_state_to_user_and_workspace(state)

        if not user_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Unable to determine user_id from state parameter",
            )

        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User not found",
            )

        # Clear installation_id from any other user that previously used it
        clear_stmt = select(User).where(
            User.github_installation_id == installation_id,
            User.id != user.id,
        )
        clear_res = await self.session.execute(clear_stmt)
        for other_user in clear_res.scalars().all():
            other_user.github_installation_id = None
            other_user.github_username = None

        user.github_installation_id = installation_id

        # Check Redis cache for early webhook delivery
        try:
            redis_client = get_redis_async_client()
            cached_str = await redis_client.get(
                f"github_installation:{installation_id}"
            )
            if cached_str:
                cached_data = json.loads(cached_str)
                gh_username = cached_data.get("username")
                if gh_username:
                    user.github_username = gh_username

                cached_repos = cached_data.get("repos", [])
                if cached_repos and workspace_id:
                    branch_service = BranchService(session=self.session)
                    for repo in cached_repos:
                        name = repo.get("name")
                        clone_url = repo.get("clone_url")
                        default_branch = repo.get("default_branch", "main")
                        if name and clone_url:
                            await branch_service.attach_repository_db(
                                workspace_id=workspace_id,
                                git_url=clone_url,
                                repo_name=name,
                                branch_names=[default_branch],
                                user_id=user.id,
                            )
        except (RedisError, ConnectionError, json.JSONDecodeError) as exc:
            logger.debug("Redis lookup for cached installation failed: %s", exc)

        await self.session.commit()

        if workspace_id:
            return f"{settings.FRONTEND_URL}/workspaces/{workspace_id}?github_connected=true"
        return f"{settings.FRONTEND_URL}/workspaces?github_connected=true"

    def get_status(self, user: User) -> GitHubStatusResponse:
        """Retrieves GitHub App installation status for the specified user.

        Args:
            user (User): Target user entity.

        Returns:
            GitHubStatusResponse: Status indicating connection state and installation metadata.
        """
        is_connected = user.github_installation_id is not None
        manage_url = (
            f"https://github.com/settings/installations/{user.github_installation_id}"
            if is_connected
            else None
        )
        return GitHubStatusResponse(
            is_connected=is_connected,
            github_installation_id=user.github_installation_id,
            github_username=user.github_username,
            manage_url=manage_url,
        )

    async def unlink_installation(self, user: User) -> GitHubStatusResponse:
        """Unlinks GitHub App installation from the specified user.

        Args:
            user (User): Target user entity.

        Returns:
            GitHubStatusResponse: Updated disconnected status.
        """
        user.github_installation_id = None
        user.github_username = None
        await self.session.commit()

        return GitHubStatusResponse(
            is_connected=False,
            github_installation_id=None,
            github_username=None,
            manage_url=None,
        )


def get_github_app_service(
    session: DBSession,
) -> GitHubAppService:
    """FastAPI dependency provider for GitHubAppService.

    Args:
        session (DBSession): Database session.

    Returns:
        GitHubAppService: Instantiated service.
    """
    return GitHubAppService(session=session)


GitHubAppServiceDep = Annotated[GitHubAppService, Depends(get_github_app_service)]
