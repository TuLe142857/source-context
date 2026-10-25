from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentAgent, DBSession
from app.core import AppException, ErrorCode
from app.model.branch import Branch
from app.model.project import Project
from app.model.repo_profile import RepoProfile
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.model.workspace_repository import WorkspaceRepository
from app.schemas.branch import SimpleBranchResponse
from app.schemas.general import RepositoryOverviewResponse
from app.schemas.project import ProjectResponse
from app.schemas.repository import SimpleRepositoryResponse
from app.schemas.subrepo_profile import SubrepoProfileResponse
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

    async def get_repository_overview(
        self,
        repository_id: int,
        workspace_id: int | None = None,
        include_readme: bool = False,
    ) -> RepositoryOverviewResponse:
        """Retrieves a comprehensive architectural overview and technical profile of a repository.

        Args:
            repository_id (int): Target repository ID.
            workspace_id (int | None, optional): Optional workspace ID. Defaults to None.
            include_readme (bool, optional): Whether to include full readme content. Defaults to False.

        Returns:
            RepositoryOverviewResponse: Detailed technical profile, subprojects, tech stack, and entrypoints.

        Raises:
            AppException: If repository is not found or not accessible.
        """
        stmt = (
            select(Repository)
            .join(
                WorkspaceRepository,
                Repository.id == WorkspaceRepository.repository_id,
            )
            .join(Workspace, Workspace.id == WorkspaceRepository.workspace_id)
            .where(
                Repository.id == repository_id,
                Workspace.owner_id == self.current_agent.id,
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(Workspace.id == workspace_id)

        stmt = stmt.options(
            selectinload(Repository.profile).selectinload(RepoProfile.subrepo_profiles)
        )

        results = await self.session.scalars(stmt)
        repo = results.first()
        if repo is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"Repository ID {repository_id} not found or inaccessible.",
            )

        if repo.profile is not None:
            profile = repo.profile
            return RepositoryOverviewResponse(
                repository_id=repo.id,
                name=repo.name,
                git_url=repo.git_url,
                profile_available=True,
                branch_name=profile.branch_name,
                commit_sha=profile.commit_sha,
                primary_language=profile.primary_language,
                summary=profile.summary,
                license_name=profile.license_name,
                topics=profile.topics,
                languages_breakdown=profile.languages_breakdown,
                readme_content=profile.readme_content if include_readme else None,
                subprojects=[
                    SubrepoProfileResponse.model_validate(sub)
                    for sub in profile.subrepo_profiles
                ],
                extra_info=profile.extra_info,
                analyzed_at=profile.analyzed_at,
            )

        return RepositoryOverviewResponse(
            repository_id=repo.id,
            name=repo.name,
            git_url=repo.git_url,
            profile_available=False,
        )


def get_general_service(
    current_agent: CurrentAgent, session: DBSession
) -> GeneralService:
    return GeneralService(session=session, current_agent=current_agent)


GeneralServiceDep = Annotated[GeneralService, Depends(get_general_service)]
