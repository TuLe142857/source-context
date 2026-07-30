from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core import AppException, ErrorCode
from app.enums import BranchIndexingStatus, IndexingJobStatus
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.member import Member
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.schemas.indexing import IndexingJobResponse, TriggerBranchIndexingRequest
from app.tasks import index_branch_task


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

    async def trigger_branch_indexing(
        self,
        workspace_id: int,
        branch_id: int,
        payload: TriggerBranchIndexingRequest | None = None,
    ) -> IndexingJobResponse:
        await self._check_workspace_access(workspace_id)

        branch_stmt = (
            select(Branch)
            .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
            .where(
                Branch.id == branch_id,
                WorkspaceBranch.workspace_id == workspace_id,
            )
        )
        branch_res = await self.session.scalars(branch_stmt)
        branch = branch_res.one_or_none()
        if branch is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Branch with ID {branch_id} not found in this workspace.",
            )

        new_commit_hashed = payload.commit_hashed if payload else None

        if branch.indexing_status == BranchIndexingStatus.INDEXING:
            raise AppException(
                error_code=ErrorCode.ACTION_CONFLICT,
                message="Branch is currently being indexed. Please wait for current process to complete.",
            )

        if branch.indexing_status == BranchIndexingStatus.INDEXED:
            if new_commit_hashed and new_commit_hashed != branch.commit_hashed:
                branch.commit_hashed = new_commit_hashed
            else:
                raise AppException(
                    error_code=ErrorCode.ACTION_ALREADY_PERFORMED,
                    message="Branch is already indexed and commit hash has not changed.",
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
                job.error_message = None
                branch.indexing_status = BranchIndexingStatus.INDEXING
                await self.session.flush()
                index_branch_task.delay(workspace_id, branch.id, job.id)
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

        index_branch_task.delay(workspace_id, branch.id, job.id)
        await self.session.commit()
        await self.session.refresh(job)

        return IndexingJobResponse.model_validate(job)

    async def trigger_workspace_indexing(
        self, workspace_id: int
    ) -> list[IndexingJobResponse]:
        await self._check_workspace_access(workspace_id)

        branches_stmt = (
            select(Branch)
            .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
            .where(WorkspaceBranch.workspace_id == workspace_id)
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
            branch.indexing_status = BranchIndexingStatus.INDEXING
            job = IndexingJob(
                workspace_id=workspace_id,
                branch_id=branch.id,
                status=IndexingJobStatus.PENDING,
                progress_pct=0,
            )
            self.session.add(job)
            await self.session.flush()

            index_branch_task.delay(workspace_id, branch.id, job.id)
            jobs.append(job)

        await self.session.commit()
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


def get_indexing_service(
    current_user: CurrentUser, session: DBSession
) -> IndexingService:
    return IndexingService(session=session, current_user=current_user)


IndexingServiceDep = Annotated[IndexingService, Depends(get_indexing_service)]
