from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies import CurrentAgent, DBSession
from app.core import AppException, ErrorCode
from app.model.branch import Branch
from app.model.project import Project
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.model.workspace_repository import WorkspaceRepository
from app.schemas.branch import SimpleBranchResponse
from app.schemas.project import ProjectResponse
from app.schemas.repository import SimpleRepositoryResponse
from app.schemas.workspace import WorkspaceResponse


class GeneralService:
    def __init__(self, session: DBSession, current_agent: CurrentAgent) -> None:
        self.session = session
        self.current_agent = current_agent

    async def get_workspaces(self) -> list[WorkspaceResponse]:
        stmt = select(Workspace).where(Workspace.owner_id == self.current_agent.id)
        results = await self.session.scalars(stmt)
        workspaces = list(results.all())
        return [WorkspaceResponse.model_validate(w) for w in workspaces]

    async def get_repositories(
        self, workspace_id: int
    ) -> list[SimpleRepositoryResponse]:
        stmt = (
            select(Repository)
            .join(
                WorkspaceRepository,
                Repository.id == WorkspaceRepository.repository_id,
            )
            .join(Workspace, Workspace.id == WorkspaceRepository.workspace_id)
            .where(Workspace.id == workspace_id)
        )
        results = await self.session.scalars(stmt)
        repos = list(results.all())
        return [SimpleRepositoryResponse.model_validate(r) for r in repos]

    async def get_branches(
        self, workspace_id: int, repository_id: int
    ) -> list[SimpleBranchResponse]:
        stmt = (
            select(Branch)
            .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
            .where(
                WorkspaceBranch.workspace_id == workspace_id,
                Branch.repository_id == repository_id,
            )
        )
        results = await self.session.scalars(stmt)
        branches = list(results.all())
        return [SimpleBranchResponse.model_validate(b) for b in branches]

    async def get_projects(
        self, workspace_id: int, repo_id: int, branch_name: str
    ) -> list[ProjectResponse]:
        branch_stmt = select(Branch).where(
            Branch.repository_id == repo_id,
            Branch.branch_name == branch_name,
        )
        branch_res = await self.session.scalars(branch_stmt)
        branch = branch_res.one_or_none()
        if branch is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Branch '{branch_name}' for repository ID {repo_id} not found.",
            )

        stmt = select(Project).where(
            Project.branch_id == branch.id,
            (Project.workspace_id == workspace_id) | (Project.workspace_id.is_(None)),
        )
        results = await self.session.scalars(stmt)
        projects = list(results.all())
        return [
            ProjectResponse(
                id=p.id,
                branch_id=p.branch_id,
                workspace_id=p.workspace_id,
                root_dir=p.root_dir,
                language=p.language,
            )
            for p in projects
        ]


def get_general_service(
    current_agent: CurrentAgent, session: DBSession
) -> GeneralService:
    return GeneralService(session=session, current_agent=current_agent)


GeneralServiceDep = Annotated[GeneralService, Depends(get_general_service)]
