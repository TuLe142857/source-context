from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core import AppException, ErrorCode
from app.enums import BranchIndexingStatus, IndexingJobStatus
from app.indexing.version import INDEX_VERSION
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.indexing_state import IndexingRun, IndexingState
from app.model.member import Member
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.repository_manager.resolver import resolve_repository_installation_id
from app.schemas.indexing import (
    IndexingJobResponse,
    IndexingRunResponse,
    IndexingStateResponse,
)
from app.tasks import index_branch_task
from app.util.git_util import get_latest_commit_hash


class IndexingService:
    def __init__(self, session: DBSession, current_user: CurrentUser) -> None:
        self.session = session
        self.current_user = current_user

    async def _check_workspace_access(self, workspace_id: int) -> Workspace:
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        res = await self.session.scalars(stmt)
        workspace = res.one_or_none()
        if workspace is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Workspace not found",
            )
        if workspace.owner_id == self.current_user.id:
            return workspace

        member_stmt = select(Member).where(
            Member.workspace_id == workspace_id,
            Member.user_id == self.current_user.id,
        )
        member_res = await self.session.scalars(member_stmt)
        if member_res.one_or_none() is None:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Access denied. You are not a member of this workspace.",
            )
        return workspace

    async def _active_run_for_target(
        self, workspace_id: int, branch_id: int
    ) -> IndexingRun | None:
        return await self.session.scalar(
            select(IndexingRun)
            .where(
                IndexingRun.workspace_id == workspace_id,
                IndexingRun.branch_id == branch_id,
                IndexingRun.status.in_(("PENDING", "QUEUED", "RUNNING", "RETRYING")),
            )
            .order_by(IndexingRun.id.desc())
        )

    async def _recover_stale_run(self, run: IndexingRun) -> bool:
        started = run.started_at or run.created_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started > datetime.now(timezone.utc) - timedelta(hours=6):
            return False
        run.status = "FAILED"
        run.current_stage = "FAILED"
        run.error_message = "Indexing worker stopped reporting progress; retry required."
        run.completed_at = datetime.now(timezone.utc)
        if run.job_id is not None:
            job = await self.session.get(IndexingJob, run.job_id)
            if job is not None and job.status != IndexingJobStatus.COMPLETED:
                job.status = IndexingJobStatus.FAILED
                job.error_message = run.error_message
        state = await self.session.get(
            IndexingState, (run.workspace_id, run.branch_id)
        )
        if state is not None:
            state.status = "FAILED"
        branch = await self.session.get(Branch, run.branch_id)
        if branch is not None:
            branch.indexing_status = BranchIndexingStatus.FAILED
        await self.session.flush()
        return True

    async def trigger_branch_indexing(
        self,
        workspace_id: int,
        branch_id: int,
        force_full: bool = False,
    ) -> IndexingJobResponse:
        await self._check_workspace_access(workspace_id)

        branch_stmt = (
            select(Branch)
            .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
            .where(
                Branch.id == branch_id,
                WorkspaceBranch.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        branch_res = await self.session.scalars(branch_stmt)
        branch = branch_res.one_or_none()
        if branch is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Branch with ID {branch_id} not found in this workspace.",
            )

        active_run = await self._active_run_for_target(workspace_id, branch_id)
        if active_run is not None and not await self._recover_stale_run(active_run):
            raise AppException(
                error_code=ErrorCode.ACTION_CONFLICT,
                message="An indexing run is already active for this branch.",
            )

        repo_stmt = select(Repository).where(Repository.id == branch.repository_id)
        repo_res = await self.session.scalars(repo_stmt)
        repo = repo_res.one_or_none()
        if repo is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Repository for branch {branch_id} not found.",
            )

        # Resolve GitHub App installation_id for private repository access
        installation_id = await resolve_repository_installation_id(
            db=self.session, repo=repo, workspace_id=workspace_id
        )

        new_commit_hashed = get_latest_commit_hash(
            repo_url=repo.git_url,
            branch_name=branch.branch_name,
            installation_id=installation_id,
        )
        if new_commit_hashed and new_commit_hashed != "HEAD":
            branch.commit_hashed = new_commit_hashed

        target_commit = new_commit_hashed or branch.commit_hashed or "HEAD"
        state = await self.session.get(
            IndexingState, (workspace_id, branch_id)
        )
        if state is None:
            state = IndexingState(
                workspace_id=workspace_id,
                branch_id=branch_id,
                status="UNINDEXED",
            )
            self.session.add(state)
        state.latest_observed_commit_sha = target_commit

        if branch.indexing_status == BranchIndexingStatus.INDEXING:
            raise AppException(
                error_code=ErrorCode.ACTION_CONFLICT,
                message="Branch is currently being indexed. Please wait for current process to complete.",
            )

        if branch.indexing_status == BranchIndexingStatus.FAILED:
            latest_job_stmt = (
                select(IndexingJob)
                .where(
                    IndexingJob.workspace_id == workspace_id,
                    IndexingJob.branch_id == branch_id,
                )
                .order_by(IndexingJob.created_at.desc())
            )
            latest_job_res = await self.session.scalars(latest_job_stmt)
            latest_job = latest_job_res.first()

            if latest_job is not None:
                job = latest_job
                job.status = IndexingJobStatus.PENDING
                job.progress_pct = 0
                job.error_message = None
                branch.indexing_status = BranchIndexingStatus.INDEXING
                state.status = "INDEXING"
                self.session.add(
                    IndexingRun(
                        workspace_id=workspace_id,
                        branch_id=branch_id,
                        job_id=job.id,
                        base_commit_sha=state.indexed_commit_sha,
                        target_commit_sha=target_commit,
                        mode="FULL",
                        fallback_reason=(
                            "Explicit full reindex requested" if force_full else None
                        ),
                        status="PENDING",
                    )
                )
                await self.session.flush()
                await self.session.commit()
                try:
                    index_branch_task.delay(workspace_id, branch.id, job.id)
                except Exception:
                    job.status = IndexingJobStatus.FAILED
                    job.error_message = "Unable to enqueue indexing task."
                    branch.indexing_status = BranchIndexingStatus.FAILED
                    state.status = "FAILED"
                    retry_run = await self.session.scalar(
                        select(IndexingRun)
                        .where(IndexingRun.job_id == job.id)
                        .order_by(IndexingRun.id.desc())
                    )
                    if retry_run is not None:
                        retry_run.status = "FAILED"
                        retry_run.error_message = "Unable to enqueue indexing task."
                    await self.session.commit()
                    raise
                await self.session.refresh(job)
                return IndexingJobResponse.model_validate(job)

        if (
            not force_full
            and branch.indexing_status == BranchIndexingStatus.INDEXED
            and state.indexed_commit_sha == target_commit
            and state.index_version == INDEX_VERSION
            and state.checkpoint_valid
        ):
            job = IndexingJob(
                workspace_id=workspace_id,
                branch_id=branch_id,
                status=IndexingJobStatus.COMPLETED,
                progress_pct=100,
            )
            self.session.add(job)
            await self.session.flush()
            self.session.add(
                IndexingRun(
                    workspace_id=workspace_id,
                    branch_id=branch_id,
                    job_id=job.id,
                    base_commit_sha=state.indexed_commit_sha,
                    target_commit_sha=target_commit,
                    mode="NOOP",
                    status="COMPLETED",
                    current_stage="COMPLETED",
                )
            )
            await self.session.commit()
            await self.session.refresh(job)
            return IndexingJobResponse.model_validate(job)

        branch.indexing_status = BranchIndexingStatus.INDEXING
        job = IndexingJob(
            workspace_id=workspace_id,
            branch_id=branch_id,
            status=IndexingJobStatus.PENDING,
            progress_pct=0,
        )
        self.session.add(job)
        await self.session.flush()

        run = IndexingRun(
            workspace_id=workspace_id,
            branch_id=branch_id,
            job_id=job.id,
            base_commit_sha=state.indexed_commit_sha,
            target_commit_sha=target_commit,
            mode="FULL",
            fallback_reason=("Explicit full reindex requested" if force_full else None),
            status="PENDING",
        )
        state.status = "INDEXING"
        self.session.add(run)

        await self.session.commit()
        try:
            index_branch_task.delay(workspace_id, branch.id, job.id)
        except Exception:
            job.status = IndexingJobStatus.FAILED
            job.error_message = "Unable to enqueue indexing task."
            branch.indexing_status = BranchIndexingStatus.FAILED
            state.status = "FAILED"
            run.status = "FAILED"
            run.error_message = "Unable to enqueue indexing task."
            await self.session.commit()
        await self.session.refresh(job)

        return IndexingJobResponse.model_validate(job)

    async def trigger_workspace_indexing(
        self, workspace_id: int, force_full: bool = False
    ) -> list[IndexingJobResponse]:
        await self._check_workspace_access(workspace_id)

        branches_stmt = (
            select(Branch)
            .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
            .where(WorkspaceBranch.workspace_id == workspace_id)
            .with_for_update()
        )
        branches_res = await self.session.scalars(branches_stmt)
        branches = list(branches_res.all())
        if not branches:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="No branches registered in this workspace to index.",
            )

        jobs: list[IndexingJob] = []
        for branch in branches:
            active_run = await self._active_run_for_target(workspace_id, branch.id)
            if active_run is not None and not await self._recover_stale_run(active_run):
                raise AppException(
                    error_code=ErrorCode.ACTION_CONFLICT,
                    message=f"An indexing run is already active for branch {branch.id}.",
                )
            repo_stmt = select(Repository).where(Repository.id == branch.repository_id)
            repo = (await self.session.scalars(repo_stmt)).one_or_none()
            if repo is not None:
                inst_id = await resolve_repository_installation_id(
                    db=self.session, repo=repo, workspace_id=workspace_id
                )
                commit_hash = get_latest_commit_hash(
                    repo_url=repo.git_url,
                    branch_name=branch.branch_name,
                    installation_id=inst_id,
                )
                if commit_hash and commit_hash != "HEAD":
                    branch.commit_hashed = commit_hash

            branch.indexing_status = BranchIndexingStatus.INDEXING
            job = IndexingJob(
                workspace_id=workspace_id,
                branch_id=branch.id,
                status=IndexingJobStatus.PENDING,
                progress_pct=0,
            )
            self.session.add(job)
            await self.session.flush()

            target_commit = branch.commit_hashed or "HEAD"
            state = await self.session.get(IndexingState, (workspace_id, branch.id))
            if state is None:
                state = IndexingState(
                    workspace_id=workspace_id,
                    branch_id=branch.id,
                    status="UNINDEXED",
                )
                self.session.add(state)
            state.latest_observed_commit_sha = target_commit
            state.status = "INDEXING"
            self.session.add(
                IndexingRun(
                    workspace_id=workspace_id,
                    branch_id=branch.id,
                    job_id=job.id,
                    base_commit_sha=state.indexed_commit_sha,
                    target_commit_sha=target_commit,
                    mode="FULL",
                    fallback_reason=(
                        "Explicit full reindex requested" if force_full else None
                    ),
                    status="PENDING",
                )
            )

            jobs.append(job)

        await self.session.commit()
        for job in jobs:
            try:
                index_branch_task.delay(workspace_id, job.branch_id, job.id)
            except Exception:
                job.status = IndexingJobStatus.FAILED
                job.error_message = "Unable to enqueue indexing task."
                state = await self.session.get(
                    IndexingState, (workspace_id, job.branch_id)
                )
                if state is not None:
                    state.status = "FAILED"
                run = await self.session.scalar(
                    select(IndexingRun)
                    .where(IndexingRun.job_id == job.id)
                    .order_by(IndexingRun.id.desc())
                )
                if run is not None:
                    run.status = "FAILED"
                    run.error_message = "Unable to enqueue indexing task."
                await self.session.commit()
                raise
        for j in jobs:
            await self.session.refresh(j)

        return [IndexingJobResponse.model_validate(j) for j in jobs]

    async def list_workspace_indexing_jobs(
        self, workspace_id: int
    ) -> list[IndexingJobResponse]:
        await self._check_workspace_access(workspace_id)

        stmt = (
            select(IndexingJob)
            .where(IndexingJob.workspace_id == workspace_id)
            .order_by(IndexingJob.created_at.desc())
        )
        res = await self.session.scalars(stmt)
        jobs = list(res.all())
        return [IndexingJobResponse.model_validate(j) for j in jobs]

    async def list_workspace_indexing_runs(
        self, workspace_id: int
    ) -> list[IndexingRunResponse]:
        await self._check_workspace_access(workspace_id)
        stmt = (
            select(IndexingRun)
            .where(IndexingRun.workspace_id == workspace_id)
            .order_by(IndexingRun.id.desc())
        )
        res = await self.session.scalars(stmt)
        responses = []
        for run in res.all():
            response = IndexingRunResponse.model_validate(run)
            response.statistics = {
                key: value
                for key, value in (run.statistics or {}).items()
                if isinstance(value, int)
            }
            responses.append(response)
        return responses

    async def list_workspace_indexing_states(
        self, workspace_id: int
    ) -> list[IndexingStateResponse]:
        await self._check_workspace_access(workspace_id)
        states = await self.session.scalars(
            select(IndexingState)
            .where(IndexingState.workspace_id == workspace_id)
            .order_by(IndexingState.branch_id)
        )
        return [IndexingStateResponse.model_validate(state) for state in states.all()]

    async def get_workspace_indexing_run(
        self, workspace_id: int, run_id: int
    ) -> IndexingRunResponse:
        await self._check_workspace_access(workspace_id)
        run = await self.session.scalar(
            select(IndexingRun).where(
                IndexingRun.id == run_id,
                IndexingRun.workspace_id == workspace_id,
            )
        )
        if run is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Indexing run {run_id} not found in this workspace.",
            )
        response = IndexingRunResponse.model_validate(run)
        response.statistics = {
            key: value
            for key, value in (run.statistics or {}).items()
            if isinstance(value, int)
        }
        return response


def get_indexing_service(
    current_user: CurrentUser, session: DBSession
) -> IndexingService:
    return IndexingService(session=session, current_user=current_user)


IndexingServiceDep = Annotated[IndexingService, Depends(get_indexing_service)]
