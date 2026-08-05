from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DBSession
from app.core import AppException, ErrorCode
from app.core.config import settings
from app.enums import BranchIndexingStatus
from app.model.branch import Branch
from app.model.member import Member
from app.model.project import Project
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.model.workspace_repository import WorkspaceRepository
from app.repository_manager.github_url import (
    GitHubUrlParser,
    fetch_github_branches,
)
from app.schemas.branch import BranchResponse
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.schemas.repository import (
    InspectGitHubBranchesRequest,
    RemoteBranchesResponse,
    RepositoryCreateRequest,
    RepositoryResponse,
    WorkspaceHierarchyResponse,
)

from app.util.git_util import get_latest_commit_hash, get_repo_name

class BranchService:
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

    async def inspect_remote_branches(
        self, payload: InspectGitHubBranchesRequest
    ) -> RemoteBranchesResponse:
        try:
            ref = GitHubUrlParser.parse(payload.git_url)
        except Exception as exc:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid GitHub URL provided: {exc}",
            ) from exc

        branches = fetch_github_branches(ref.owner, ref.repository)

        return RemoteBranchesResponse(
            git_url=ref.clone_url,
            owner=ref.owner,
            repo_name=ref.repository,
            branches=branches,
        )

    async def list_workspace_branches(
        self, workspace_id: int, repository_id: int | None = None
    ) -> list[BranchResponse]:
        await self._check_workspace_access(workspace_id)

        stmt = (
            select(Branch)
            .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
            .options(selectinload(Branch.projects))
            .where(WorkspaceBranch.workspace_id == workspace_id)
        )
        if repository_id is not None:
            stmt = stmt.where(Branch.repository_id == repository_id)

        res = await self.session.scalars(stmt)
        branches = list(res.all())

        return [
            BranchResponse(
                id=b.id,
                repository_id=b.repository_id,
                branch_name=b.branch_name,
                commit_hashed=b.commit_hashed,
                indexing_status=b.indexing_status,
                local_path=b.local_path,
                projects=[
                    ProjectResponse(
                        id=p.id,
                        branch_id=p.branch_id,
                        workspace_id=p.workspace_id,
                        root_dir=p.root_dir,
                        language=p.language,
                    )
                    for p in b.projects
                    if p.workspace_id is None or p.workspace_id == workspace_id
                ],
            )
            for b in branches
        ]

    async def is_branch_exist_in_workspace(branch_name: str, workspace_id: int) -> bool:
        pass


    async def attach_repository(
        self, workspace_id: int, payload: RepositoryCreateRequest
    ) -> RepositoryResponse:
        await self._check_workspace_access(workspace_id)

        repo_stmt = select(Repository).where(Repository.git_url == payload.git_url)
        repo_res = await self.session.scalars(repo_stmt)
        repo = repo_res.one_or_none()
        repo_name = get_repo_name(repo_url=payload.git_url)
        if repo is None:
            
            repo = Repository(
                name=repo_name,
                git_url=payload.git_url,
            )
            self.session.add(repo)
            await self.session.flush()

        link_stmt = select(WorkspaceRepository).where(
            WorkspaceRepository.workspace_id == workspace_id,
            WorkspaceRepository.repository_id == repo.id,
        )
        link_res = await self.session.scalars(link_stmt)
        if link_res.one_or_none() is None:
            self.session.add(
                WorkspaceRepository(workspace_id=workspace_id, repository_id=repo.id)
            )

        for branch_req in payload.branches:
            branch_stmt = select(Branch).where(
                Branch.repository_id == repo.id,
                Branch.branch_name == branch_req.branch_name,
            )
            branch_res = await self.session.scalars(branch_stmt)
            existing_branch = branch_res.one_or_none()

            commit_hashed = get_latest_commit_hash(repo_url=repo.git_url, branch_name=branch_req.branch_name)

            if existing_branch is None:
                local_path = f"{settings.repository_workspace_root}/ws_{workspace_id}/{repo_name}/{branch_req.branch_name}"
                target_branch = Branch(
                    repository_id=repo.id,
                    branch_name=branch_req.branch_name,
                    commit_hashed=commit_hashed,
                    indexing_status=BranchIndexingStatus.UNINDEXED,
                    local_path=local_path,
                )
                self.session.add(target_branch)
                await self.session.flush()
            else:
                target_branch = existing_branch
                if commit_hashed and commit_hashed != "HEAD":
                    if target_branch.commit_hashed != commit_hashed:
                        target_branch.commit_hashed = commit_hashed
                        if (
                            target_branch.indexing_status
                            == BranchIndexingStatus.INDEXED
                        ):
                            target_branch.indexing_status = (
                                BranchIndexingStatus.OUTDATED
                            )

            wb_stmt = select(WorkspaceBranch).where(
                WorkspaceBranch.workspace_id == workspace_id,
                WorkspaceBranch.branch_id == target_branch.id,
            )
            wb_res = await self.session.scalars(wb_stmt)
            if wb_res.one_or_none() is None:
                self.session.add(
                    WorkspaceBranch(
                        workspace_id=workspace_id,
                        branch_id=target_branch.id,
                    )
                )

        await self.session.commit()

        wb_all_stmt = select(WorkspaceBranch.branch_id).where(
            WorkspaceBranch.workspace_id == workspace_id
        )
        wb_all_res = await self.session.scalars(wb_all_stmt)
        ws_branch_ids = set(wb_all_res.all())

        stmt = (
            select(Repository)
            .where(Repository.id == repo.id)
            .options(selectinload(Repository.branches).selectinload(Branch.projects))
        )
        res = await self.session.scalars(stmt)
        created_repo = res.one()

        return RepositoryResponse(
            id=created_repo.id,
            name=created_repo.name,
            git_url=created_repo.git_url,
            branches=[
                BranchResponse(
                    id=b.id,
                    repository_id=b.repository_id,
                    branch_name=b.branch_name,
                    commit_hashed=b.commit_hashed,
                    indexing_status=b.indexing_status,
                    local_path=b.local_path,
                    projects=[
                        ProjectResponse(
                            id=p.id,
                            branch_id=p.branch_id,
                            workspace_id=p.workspace_id,
                            root_dir=p.root_dir,
                            language=p.language,
                        )
                        for p in b.projects
                        if p.workspace_id is None or p.workspace_id == workspace_id
                    ],
                )
                for b in created_repo.branches
                if b.id in ws_branch_ids
            ],
        )

    async def create_or_config_subproject(
        self, workspace_id: int, branch_id: int, payload: ProjectCreateRequest
    ) -> ProjectResponse:
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

        proj_stmt = select(Project).where(
            Project.workspace_id == workspace_id,
            Project.branch_id == branch_id,
            Project.root_dir == payload.root_dir,
        )
        proj_res = await self.session.scalars(proj_stmt)
        existing_project = proj_res.one_or_none()

        if existing_project is not None:
            existing_project.language = payload.language
            project = existing_project
        else:
            project = Project(
                workspace_id=workspace_id,
                branch_id=branch_id,
                root_dir=payload.root_dir,
                language=payload.language,
            )
            self.session.add(project)

        await self.session.commit()
        await self.session.refresh(project)

        return ProjectResponse(
            id=project.id,
            branch_id=project.branch_id,
            workspace_id=project.workspace_id,
            root_dir=project.root_dir,
            language=project.language,
        )

    async def update_subproject(
        self, workspace_id: int, project_id: int, payload: ProjectUpdateRequest
    ) -> ProjectResponse:
        await self._check_workspace_access(workspace_id)

        proj_stmt = select(Project).where(
            Project.id == project_id,
            (Project.workspace_id == workspace_id) | (Project.workspace_id.is_(None)),
        )
        proj_res = await self.session.scalars(proj_stmt)
        project = proj_res.one_or_none()
        if project is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Subproject with ID {project_id} not found in this workspace.",
            )

        if payload.root_dir is not None:
            project.root_dir = payload.root_dir
        if payload.language is not None:
            project.language = payload.language

        await self.session.commit()
        await self.session.refresh(project)

        return ProjectResponse(
            id=project.id,
            branch_id=project.branch_id,
            workspace_id=project.workspace_id,
            root_dir=project.root_dir,
            language=project.language,
        )

    async def delete_subproject(self, workspace_id: int, project_id: int) -> None:
        await self._check_workspace_access(workspace_id)

        proj_stmt = select(Project).where(
            Project.id == project_id,
            (Project.workspace_id == workspace_id) | (Project.workspace_id.is_(None)),
        )
        proj_res = await self.session.scalars(proj_stmt)
        project = proj_res.one_or_none()
        if project is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Project with ID {project_id} not found in this workspace.",
            )

        await self.session.delete(project)
        await self.session.commit()

    async def get_workspace_hierarchy(
        self, workspace_id: int
    ) -> WorkspaceHierarchyResponse:
        await self._check_workspace_access(workspace_id)

        wb_all_stmt = select(WorkspaceBranch.branch_id).where(
            WorkspaceBranch.workspace_id == workspace_id
        )
        wb_all_res = await self.session.scalars(wb_all_stmt)
        ws_branch_ids = set(wb_all_res.all())

        stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(
                selectinload(Workspace.members),
                selectinload(Workspace.repositories)
                .selectinload(Repository.branches)
                .selectinload(Branch.projects),
            )
        )
        res = await self.session.scalars(stmt)
        ws = res.one()

        return WorkspaceHierarchyResponse(
            id=ws.id,
            workspace_name=ws.workspace_name,
            owner_id=ws.owner_id,
            members=[],
            repositories=[
                RepositoryResponse(
                    id=r.id,
                    name=r.name,
                    git_url=r.git_url,
                    branches=[
                        BranchResponse(
                            id=b.id,
                            repository_id=b.repository_id,
                            branch_name=b.branch_name,
                            commit_hashed=b.commit_hashed,
                            indexing_status=b.indexing_status,
                            local_path=b.local_path,
                            projects=[
                                ProjectResponse(
                                    id=p.id,
                                    branch_id=p.branch_id,
                                    workspace_id=p.workspace_id,
                                    root_dir=p.root_dir,
                                    language=p.language,
                                )
                                for p in b.projects
                                if p.workspace_id is None
                                or p.workspace_id == workspace_id
                            ],
                        )
                        for b in r.branches
                        if b.id in ws_branch_ids
                    ],
                )
                for r in ws.repositories
            ],
        )

    async def remove_branch_from_workspace(
        self, workspace_id: int, branch_id: int
    ) -> None:
        await self._check_workspace_access(workspace_id)

        wb_stmt = select(WorkspaceBranch).where(
            WorkspaceBranch.workspace_id == workspace_id,
            WorkspaceBranch.branch_id == branch_id,
        )
        wb_res = await self.session.scalars(wb_stmt)
        wb = wb_res.one_or_none()
        if wb is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Branch with ID {branch_id} not found in this workspace.",
            )

        await self.session.delete(wb)
        await self.session.commit()

    async def remove_repository_from_workspace(
        self, workspace_id: int, repository_id: int
    ) -> None:
        await self._check_workspace_access(workspace_id)

        link_stmt = select(WorkspaceRepository).where(
            WorkspaceRepository.workspace_id == workspace_id,
            WorkspaceRepository.repository_id == repository_id,
        )
        link_res = await self.session.scalars(link_stmt)
        link = link_res.one_or_none()
        if link is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Repository with ID {repository_id} not found in this workspace.",
            )

        wb_branches_stmt = (
            select(WorkspaceBranch)
            .join(Branch, WorkspaceBranch.branch_id == Branch.id)
            .where(
                WorkspaceBranch.workspace_id == workspace_id,
                Branch.repository_id == repository_id,
            )
        )
        wb_res = await self.session.scalars(wb_branches_stmt)
        for wb in wb_res.all():
            await self.session.delete(wb)

        await self.session.delete(link)
        await self.session.commit()


def get_branch_service(current_user: CurrentUser, session: DBSession) -> BranchService:
    return BranchService(session=session, current_user=current_user)


BranchServiceDep = Annotated[BranchService, Depends(get_branch_service)]
