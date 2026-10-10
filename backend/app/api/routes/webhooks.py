import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import DBSession, RedisDep
from app.core.config import settings
from app.enums import BranchIndexingStatus, IndexingJobStatus
from app.github_app import GitHubAppError, github_app_client
from app.github_install_state import consume_install_state
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.github_webhook_delivery import GitHubWebhookDelivery
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.services.branch_service import BranchService
from app.tasks.indexing import index_branch_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def replay_webhook_delivery_jobs(delivery_id: str, db: DBSession) -> bool:
    """Retry pending jobs after an ambiguous/failed broker publish."""

    delivery = await db.get(GitHubWebhookDelivery, delivery_id)
    if delivery is None or delivery.status not in {"QUEUE_FAILED", "QUEUED"}:
        return False
    jobs = await db.scalars(
        select(IndexingJob).where(IndexingJob.id.in_(delivery.job_ids))
    )
    pending_jobs = list(jobs.all())
    delivery.status = "QUEUED"
    await db.commit()
    try:
        for job in pending_jobs:
            index_branch_task.delay(job.workspace_id, job.branch_id, job.id)
    except Exception:
        logger.exception(
            "Retrying GitHub delivery %s could not enqueue all jobs", delivery_id
        )
        delivery.status = "QUEUE_FAILED"
        await db.commit()
        return False
    return True


async def finish_webhook_delivery(
    delivery_id: str,
    db: DBSession,
    *,
    status_value: str = "PROCESSED",
    job_ids: list[int] | None = None,
) -> None:
    delivery = await db.get(GitHubWebhookDelivery, delivery_id)
    if delivery is not None:
        delivery.status = status_value
        delivery.job_ids = job_ids or []
        delivery.processed_at = datetime.now(UTC)
    await db.commit()


async def resolve_installation_workspace(
    state: str,
    installation_id: int,
    redis: RedisDep,
) -> int:
    """Validate and consume signed state, and ensure the installation is ours."""

    try:
        belongs_to_app = github_app_client.installation_belongs_to_app(installation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid installation ID.",
        ) from exc
    except GitHubAppError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if not belongs_to_app:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Installation does not belong to this GitHub App.",
        )

    try:
        workspace_id = await consume_install_state(state, redis)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used installation state.",
        ) from exc
    return workspace_id


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
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.error("GitHub webhook secret is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub webhook is not configured.",
        )
    if not await verify_signature(request):
        logger.warning("GitHub webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    event = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not event or not delivery_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing GitHub event or delivery ID.",
        )

    payload = await request.json()

    existing_delivery = await db.get(GitHubWebhookDelivery, delivery_id)
    if existing_delivery is not None:
        if await replay_webhook_delivery_jobs(delivery_id, db):
            return {"status": "requeued", "delivery_id": delivery_id}
        return {"status": "duplicate", "delivery_id": delivery_id}

    # Keep delivery registration and the database changes it causes in one
    # transaction. A duplicate delivery then observes the committed row only
    # after its original event has completed.
    db.add(
        GitHubWebhookDelivery(
            delivery_id=delivery_id,
            event_type=event,
            action=payload.get("action"),
            status="PROCESSING",
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        if await replay_webhook_delivery_jobs(delivery_id, db):
            return {"status": "requeued", "delivery_id": delivery_id}
        return {"status": "duplicate", "delivery_id": delivery_id}

    logger.info("Received GitHub webhook event: %s", event)

    if event == "push":
        ref = payload.get("ref", "")
        if not ref.startswith("refs/heads/"):
            await finish_webhook_delivery(delivery_id, db)
            return {"status": "ignored", "reason": "not a branch push"}

        branch_name = ref[len("refs/heads/") :]
        clone_url = payload.get("repository", {}).get("clone_url")
        new_commit_hash = payload.get("after")

        if not clone_url or not new_commit_hash:
            await finish_webhook_delivery(delivery_id, db)
            return {
                "status": "ignored",
                "reason": "missing repository details or commit hash",
            }

        # Find repository
        remote_repository_id = payload.get("repository", {}).get("id")
        repo_obj = None
        if remote_repository_id is not None:
            repo_obj = await db.scalar(
                select(Repository).where(
                    Repository.github_repository_id == remote_repository_id
                )
            )
        if repo_obj is None:
            repo_obj = await db.scalar(
                select(Repository).where(
                    Repository.git_url.in_([clone_url, clone_url.removesuffix(".git")])
                )
            )
        if repo_obj is None:
            await finish_webhook_delivery(delivery_id, db)
            return {"status": "ignored", "reason": "repository not found in system"}
        if remote_repository_id is not None:
            repo_obj.github_repository_id = remote_repository_id

        # Find all branch records linked to this repository and branch name
        branch_stmt = (
            select(Branch, WorkspaceBranch.workspace_id)
            .join(WorkspaceBranch, WorkspaceBranch.branch_id == Branch.id)
            .where(
                Branch.repository_id == repo_obj.id,
                Branch.branch_name == branch_name,
            )
            .with_for_update(of=Branch)
        )
        branch_res = await db.execute(branch_stmt)
        tracked_branches = list(branch_res.all())

        if new_commit_hash == "0" * 40:
            for branch, _workspace_id in tracked_branches:
                branch.indexing_status = BranchIndexingStatus.OUTDATED
            delivery = await db.get(GitHubWebhookDelivery, delivery_id)
            if delivery is not None:
                delivery.status = "PROCESSED"
                delivery.processed_at = datetime.now(UTC)
            await db.commit()
            return {
                "status": "ok",
                "deleted_branch": True,
                "tracked_branches": len(tracked_branches),
                "cleanup_required": True,
            }

        jobs_to_queue: list[tuple[int, int, int]] = []
        changed_count = 0
        for branch, workspace_id in tracked_branches:
            prior_sha = branch.commit_hashed
            branch.commit_hashed = new_commit_hash
            if prior_sha != new_commit_hash:
                changed_count += 1
            if branch.indexed_commit_sha == new_commit_hash:
                branch.indexing_status = BranchIndexingStatus.INDEXED
                continue
            if branch.indexing_status != BranchIndexingStatus.INDEXING:
                branch.indexing_status = BranchIndexingStatus.INDEXING
                job = IndexingJob(
                    workspace_id=workspace_id,
                    branch_id=branch.id,
                    status=IndexingJobStatus.PENDING,
                    progress_pct=0,
                )
                db.add(job)
                await db.flush()
                jobs_to_queue.append((workspace_id, branch.id, job.id))

        delivery = await db.get(GitHubWebhookDelivery, delivery_id)
        if delivery is not None:
            delivery.status = "QUEUED" if jobs_to_queue else "PROCESSED"
            delivery.job_ids = [job_id for _, _, job_id in jobs_to_queue]
            delivery.processed_at = datetime.now(UTC)
        await db.commit()
        try:
            for workspace_id, branch_id, job_id in jobs_to_queue:
                index_branch_task.delay(workspace_id, branch_id, job_id)
        except Exception:
            logger.exception(
                "Could not enqueue all jobs for GitHub delivery %s", delivery_id
            )
            if delivery is not None:
                delivery.status = "QUEUE_FAILED"
                await db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook was recorded but indexing jobs could not be queued; GitHub may retry.",
            )
        return {
            "status": "ok",
            "tracked_branch_updates": changed_count,
            "jobs_queued": len(jobs_to_queue),
        }

    action = payload.get("action")
    installation_id = payload.get("installation", {}).get("id")

    if not installation_id:
        logger.warning("Webhook payload missing installation.id")
        await finish_webhook_delivery(delivery_id, db)
        return {"status": "ignored", "reason": "no installation_id"}

    repos = []
    if event == "installation_repositories" and action == "added":
        repos = payload.get("repositories_added", [])
    elif event == "installation" and action == "created":
        repos = payload.get("repositories", [])
    else:
        await finish_webhook_delivery(delivery_id, db)
        return {
            "status": "ignored",
            "reason": f"unhandled event/action: {event}/{action}",
        }

    if not repos:
        await finish_webhook_delivery(delivery_id, db)
        return {"status": "ignored", "reason": "no repositories found in event"}

    # Find workspaces linked to this installation
    stmt = select(Workspace).where(Workspace.github_installation_id == installation_id)
    res = await db.execute(stmt)
    workspaces = list(res.scalars().all())

    if not workspaces:
        logger.warning(
            "No workspaces found matching installation_id: %s", installation_id
        )
        await finish_webhook_delivery(delivery_id, db)
        return {
            "status": "ignored",
            "reason": f"no workspace linked to installation_id {installation_id}",
        }

    # Initialize BranchService
    branch_service = BranchService(session=db)

    tracked_count = 0
    queued_install_jobs: list[tuple[int, int, int]] = []
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
                github_repository_id=repo.get("id"),
            )

            # 2. Get the branch model
            branch_stmt = select(Branch).where(
                Branch.repository_id == repo_obj.id,
                Branch.branch_name == default_branch,
            )
            branch_res = await db.execute(branch_stmt)
            branch_obj = branch_res.scalar_one()

            if (
                branch_obj.indexing_status == BranchIndexingStatus.INDEXING
                or branch_obj.indexed_commit_sha == branch_obj.commit_hashed
            ):
                logger.info(
                    "Branch %s is already indexing or current, skipping.", branch_obj.id
                )
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

            # The job is committed with the delivery record below, then queued.
            # This keeps repeated GitHub deliveries from creating duplicate jobs.
            queued_install_jobs.append((workspace.id, branch_obj.id, job.id))
            tracked_count += 1

    delivery = await db.get(GitHubWebhookDelivery, delivery_id)
    if delivery is not None:
        delivery.status = "QUEUED" if tracked_count else "PROCESSED"
        delivery.job_ids = [job_id for _, _, job_id in queued_install_jobs]
        delivery.processed_at = datetime.now(UTC)
    await db.commit()
    try:
        for workspace_id, branch_id, job_id in queued_install_jobs:
            index_branch_task.delay(workspace_id, branch_id, job_id)
    except Exception:
        logger.exception(
            "Could not enqueue all jobs for GitHub delivery %s", delivery_id
        )
        if delivery is not None:
            delivery.status = "QUEUE_FAILED"
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook was recorded but indexing jobs could not be queued; GitHub may retry.",
        )
    return {"status": "ok", "repositories_tracked": tracked_count}


@router.get("/callback")
async def github_callback(
    db: DBSession,
    redis: RedisDep,
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state"
        )

    workspace_id = await resolve_installation_workspace(state, installation_id, redis)

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
    redis: RedisDep,
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state"
        )

    workspace_id = await resolve_installation_workspace(state, installation_id, redis)

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
