import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import DBSession
from app.core.config import settings
from app.enums import BranchIndexingStatus, IndexingJobStatus
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.services.branch_service import BranchService
from app.tasks.indexing import index_branch_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_signature(request: Request) -> bool:
    """Verifies that the webhook request is signed with the correct secret."""
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        return False
    payload = await request.body()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    computed = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    db: DBSession,
) -> dict[str, Any]:
    """GitHub App webhook endpoint for handling repository installations and additions."""
    if settings.GITHUB_WEBHOOK_SECRET:
        if not await verify_signature(request):
            logger.warning("GitHub webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    event = request.headers.get("X-GitHub-Event")
    payload = await request.json()

    logger.info("Received GitHub webhook event: %s", event)

    if event == "push":
        ref = payload.get("ref", "")
        if not ref.startswith("refs/heads/"):
            return {"status": "ignored", "reason": "not a branch push"}

        branch_name = ref[len("refs/heads/") :]
        clone_url = payload.get("repository", {}).get("clone_url")
        new_commit_hash = payload.get("after")

        if not clone_url or not new_commit_hash:
            return {
                "status": "ignored",
                "reason": "missing repository details or commit hash",
            }

        # Find repository
        repo_stmt = select(Repository).where(Repository.git_url == clone_url)
        repo_res = await db.execute(repo_stmt)
        repo_obj = repo_res.scalar_one_or_none()

        if not repo_obj:
            repo_stmt = select(Repository).where(Repository.git_url == clone_url.removesuffix(".git"))
            repo_res = await db.execute(repo_stmt)
            repo_obj = repo_res.scalar_one_or_none()
            if not repo_obj:
                logger.info("r2")
                return {"status": "ignored", "reason": "repository not found in system"}
            return {"status": "ignored", "reason": "repository not found in system"}

        # Find all branch records linked to this repository and branch name
        branch_stmt = select(Branch).where(
            Branch.repository_id == repo_obj.id,
            Branch.branch_name == branch_name,
        )
        branch_res = await db.execute(branch_stmt)
        branches = list(branch_res.scalars().all())

        updated_count = 0
        for branch in branches:
            if branch.indexing_status == BranchIndexingStatus.INDEXED:
                branch.indexing_status = BranchIndexingStatus.OUTDATED
                updated_count += 1

        await db.commit()
        return {"status": "ok", "branches_updated_to_outdated": updated_count}

    action = payload.get("action")
    installation_id = payload.get("installation", {}).get("id")

    if not installation_id:
        logger.warning("Webhook payload missing installation.id")
        return {"status": "ignored", "reason": "no installation_id"}

    repos = []
    if event == "installation_repositories" and action == "added":
        repos = payload.get("repositories_added", [])
    elif event == "installation" and action == "created":
        repos = payload.get("repositories", [])
    else:
        return {
            "status": "ignored",
            "reason": f"unhandled event/action: {event}/{action}",
        }

    if not repos:
        return {"status": "ignored", "reason": "no repositories found in event"}

    # Find workspaces linked to this installation
    stmt = select(Workspace).where(Workspace.github_installation_id == installation_id)
    res = await db.execute(stmt)
    workspaces = list(res.scalars().all())

    if not workspaces:
        logger.warning(
            "No workspaces found matching installation_id: %s", installation_id
        )
        return {
            "status": "ignored",
            "reason": f"no workspace linked to installation_id {installation_id}",
        }

    # Initialize BranchService
    branch_service = BranchService(session=db)

    tracked_count = 0
    for workspace in workspaces:
        for repo in repos:
            name = repo.get("name")
            clone_url = repo.get("clone_url")
            default_branch = repo.get("default_branch", "main")

            if not name or not clone_url:
                continue

            # 1. Attach repository and default branch using BranchService helper
            repo_obj = await branch_service.attach_repository_db(
                workspace_id=workspace.id,
                git_url=clone_url,
                repo_name=name,
                branch_names=[default_branch],
            )

            # 2. Get the branch model
            branch_stmt = select(Branch).where(
                Branch.repository_id == repo_obj.id,
                Branch.branch_name == default_branch,
            )
            branch_res = await db.execute(branch_stmt)
            branch_obj = branch_res.scalar_one()

            if branch_obj.indexing_status == BranchIndexingStatus.INDEXING:
                logger.info("Branch %s is already indexing, skipping.", branch_obj.id)
                continue

            branch_obj.indexing_status = BranchIndexingStatus.INDEXING

            # 3. Create IndexingJob
            job = IndexingJob(
                workspace_id=workspace.id,
                branch_id=branch_obj.id,
                status=IndexingJobStatus.PENDING,
                progress_pct=0,
            )
            db.add(job)
            await db.flush()

            await db.commit()

            # Trigger indexing Celery task
            index_branch_task.delay(workspace.id, branch_obj.id, job.id)
            tracked_count += 1

    return {"status": "ok", "repositories_tracked": tracked_count}


@router.get("/callback")
async def github_callback(
    db: DBSession,
    code: str | None = None,
    installation_id: int | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Redirect callback endpoint for GitHub App installation completion."""
    if not installation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing installation_id",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state (workspace_id)",
        )

    try:
        workspace_id = int(state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace_id in state",
        ) from exc

    # Fetch workspace
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    res = await db.execute(stmt)
    workspace = res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Update installation id
    workspace.github_installation_id = installation_id
    await db.commit()

    # Redirect back to the frontend workspace details page
    redirect_url = f"{settings.FRONTEND_URL}/workspaces/{workspace_id}"
    return RedirectResponse(url=redirect_url)


@router.get("/setup")
async def github_setup(
    db: DBSession,
    installation_id: int | None = None,
    setup_action: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Redirect setup endpoint for GitHub App installation completion.

    Args:
        db (DBSession): Async database session.
        installation_id (int | None, optional): The GitHub installation ID. Defaults to None.
        setup_action (str | None, optional): The action performed. Defaults to None.
        state (str | None, optional): The workspace ID passed as state. Defaults to None.

    Returns:
        RedirectResponse: Redirect to the frontend workspace details page.
    """
    if not installation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing installation_id",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state (workspace_id)",
        )

    try:
        workspace_id = int(state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace_id in state",
        ) from exc

    # Fetch workspace
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    res = await db.execute(stmt)
    workspace = res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Update installation id
    workspace.github_installation_id = installation_id
    await db.commit()

    # Redirect back to the frontend workspace details page
    redirect_url = f"{settings.FRONTEND_URL}/workspaces/{workspace_id}"
    return RedirectResponse(url=redirect_url)
