"""API routes for Repository, Branch, and Sub-Project configuration under Workspaces."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DBSession
from app.api.routes.workspaces import check_workspace_access
from app.indexing.tasks import index_branch_task
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.project import Project
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.repository_manager.github_url import (
    GitHubUrlParser,
    fetch_github_branches,
)
from app.schemas.branch import BranchResponse
from app.schemas.indexing import IndexingJobResponse
from app.schemas.project import ProjectCreateRequest, ProjectResponse
from app.schemas.repository import (
    InspectGitHubBranchesRequest,
    RemoteBranchesResponse,
    RepositoryCreateRequest,
    RepositoryResponse,
    WorkspaceHierarchyResponse,
)

router = APIRouter(prefix="/workspaces", tags=["Workspace Repositories & Hierarchy"])


@router.post(
    "/{workspace_id}/repositories/inspect-branches",
    response_model=RemoteBranchesResponse,
    summary="Inspect GitHub repository URL and list remote branches",
)
async def inspect_remote_branches(
    workspace_id: int,
    payload: InspectGitHubBranchesRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> RemoteBranchesResponse:
    """Parses GitHub URL and returns list of available remote branch names.

    Args:
        workspace_id (int): Target workspace ID.
        payload (InspectGitHubBranchesRequest): GitHub URL.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        RemoteBranchesResponse: Repository owner, name, and list of branch names.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    try:
        ref = GitHubUrlParser.parse(payload.git_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub URL provided: {exc}",
        ) from exc

    branches = fetch_github_branches(ref.owner, ref.repository)

    return RemoteBranchesResponse(
        git_url=ref.clone_url,
        owner=ref.owner,
        repo_name=ref.repository,
        branches=branches,
    )


@router.post(
    "/{workspace_id}/repositories",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a repository and register selected branches to workspace",
)
async def create_repository_with_branches(
    workspace_id: int,
    payload: RepositoryCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> RepositoryResponse:
    """Creates a Repository record and registers selected Branch records with persistent local paths.

    Args:
        workspace_id (int): Target workspace ID.
        payload (RepositoryCreateRequest): Repository details and branches.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        RepositoryResponse: Created repository and registered branch information.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    repo = Repository(
        project_id=workspace_id,
        name=payload.name,
        git_url=payload.git_url,
    )
    db.add(repo)
    await db.flush()

    for branch_req in payload.branches:
        local_path = f"/app/workspace-repositories/ws_{workspace_id}/{payload.name}/{branch_req.branch_name}"
        branch = Branch(
            repository_id=repo.id,
            branch_name=branch_req.branch_name,
            commit_hashed=branch_req.commit_hashed,
            local_path=local_path,
        )
        db.add(branch)

    await db.commit()

    res = await db.execute(
        select(Repository)
        .where(Repository.id == repo.id)
        .options(selectinload(Repository.branches).selectinload(Branch.projects))
    )
    created_repo = res.scalar_one()

    return RepositoryResponse(
        id=created_repo.id,
        project_id=created_repo.project_id,
        name=created_repo.name,
        git_url=created_repo.git_url,
        branches=[
            BranchResponse(
                id=b.id,
                repository_id=b.repository_id,
                branch_name=b.branch_name,
                commit_hashed=b.commit_hashed,
                local_path=b.local_path,
                projects=[
                    ProjectResponse(
                        id=p.id,
                        branch_id=p.branch_id,
                        root_dir=p.root_dir,
                        language=p.language,
                    )
                    for p in b.projects
                ],
            )
            for b in created_repo.branches
        ],
    )


@router.post(
    "/{workspace_id}/branches/{branch_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure a sub-project (SCIP target) under a branch",
)
async def create_project_under_branch(
    workspace_id: int,
    branch_id: int,
    payload: ProjectCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectResponse:
    """Configures a Project sub-directory and language target under a specific branch.

    Args:
        workspace_id (int): Target workspace ID.
        branch_id (int): Target branch ID.
        payload (ProjectCreateRequest): Sub-directory root_dir and language.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        ProjectResponse: Created sub-project configuration.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    branch_res = await db.execute(
        select(Branch)
        .join(Repository, Branch.repository_id == Repository.id)
        .where(Branch.id == branch_id, Repository.project_id == workspace_id)
    )
    branch = branch_res.scalar_one_or_none()
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch with ID {branch_id} not found in this workspace.",
        )

    project = Project(
        branch_id=branch_id,
        root_dir=payload.root_dir,
        language=payload.language,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        branch_id=project.branch_id,
        root_dir=project.root_dir,
        language=project.language,
    )


@router.get(
    "/{workspace_id}/hierarchy",
    response_model=WorkspaceHierarchyResponse,
    summary="Get full hierarchy tree of a workspace",
)
async def get_workspace_hierarchy(
    workspace_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> WorkspaceHierarchyResponse:
    """Retrieves full nested hierarchy tree of a workspace.

    Args:
        workspace_id (int): Target workspace ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        WorkspaceHierarchyResponse: Nested hierarchy tree.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

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
    res = await db.execute(stmt)
    ws = res.scalar_one()

    return WorkspaceHierarchyResponse(
        id=ws.id,
        workspace_name=ws.workspace_name,
        owner_id=ws.owner_id,
        members=[],
        repositories=[
            RepositoryResponse(
                id=r.id,
                project_id=r.project_id,
                name=r.name,
                git_url=r.git_url,
                branches=[
                    BranchResponse(
                        id=b.id,
                        repository_id=b.repository_id,
                        branch_name=b.branch_name,
                        commit_hashed=b.commit_hashed,
                        local_path=b.local_path,
                        projects=[
                            ProjectResponse(
                                id=p.id,
                                branch_id=p.branch_id,
                                root_dir=p.root_dir,
                                language=p.language,
                            )
                            for p in b.projects
                        ],
                    )
                    for b in r.branches
                ],
            )
            for r in ws.repositories
        ],
    )


@router.delete(
    "/{workspace_id}/repositories/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a repository from a workspace",
)
async def delete_repository(
    workspace_id: int,
    repository_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Deletes a repository and all its branches and configured projects.

    Args:
        workspace_id (int): Target workspace ID.
        repository_id (int): Target repository ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    repo_res = await db.execute(
        select(Repository).where(
            Repository.id == repository_id, Repository.project_id == workspace_id
        )
    )
    repo = repo_res.scalar_one_or_none()
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repository_id} not found in this workspace.",
        )

    await db.delete(repo)
    await db.commit()


@router.delete(
    "/{workspace_id}/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a configured sub-project from a branch",
)
async def delete_sub_project(
    workspace_id: int,
    project_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Deletes a sub-project configuration.

    Args:
        workspace_id (int): Target workspace ID.
        project_id (int): Target project ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    proj_res = await db.execute(
        select(Project)
        .join(Branch, Project.branch_id == Branch.id)
        .join(Repository, Branch.repository_id == Repository.id)
        .where(Project.id == project_id, Repository.project_id == workspace_id)
    )
    project = proj_res.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found in this workspace.",
        )

    await db.delete(project)
    await db.commit()


# --- Indexing Pipeline Trigger & Status Routes ---


@router.post(
    "/{workspace_id}/index",
    response_model=list[IndexingJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger indexing pipeline for all branches in a workspace",
)
async def trigger_workspace_indexing(
    workspace_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> list[IndexingJob]:
    """Enqueues indexing jobs for all branches registered under the workspace.

    Args:
        workspace_id (int): Target workspace ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        list[IndexingJob]: Created indexing job records.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    branches_res = await db.execute(
        select(Branch)
        .join(Repository, Branch.repository_id == Repository.id)
        .where(Repository.project_id == workspace_id)
    )
    branches = branches_res.scalars().all()
    if not branches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No branches registered in this workspace to index.",
        )

    jobs: list[IndexingJob] = []
    for branch in branches:
        job = IndexingJob(
            workspace_id=workspace_id,
            branch_id=branch.id,
            status="PENDING",
            progress_pct=0,
        )
        db.add(job)
        await db.flush()

        # Dispatch Celery background task
        index_branch_task.delay(branch.id, job.id)
        jobs.append(job)

    await db.commit()
    for j in jobs:
        await db.refresh(j)
    return jobs


@router.post(
    "/{workspace_id}/branches/{branch_id}/index",
    response_model=IndexingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger indexing pipeline for a single branch",
)
async def trigger_branch_indexing(
    workspace_id: int,
    branch_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> IndexingJob:
    """Enqueues an indexing job for a specific branch.

    Args:
        workspace_id (int): Target workspace ID.
        branch_id (int): Target branch ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        IndexingJob: Created indexing job record.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    branch_res = await db.execute(
        select(Branch)
        .join(Repository, Branch.repository_id == Repository.id)
        .where(Branch.id == branch_id, Repository.project_id == workspace_id)
    )
    branch = branch_res.scalar_one_or_none()
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch with ID {branch_id} not found in this workspace.",
        )

    job = IndexingJob(
        workspace_id=workspace_id,
        branch_id=branch_id,
        status="PENDING",
        progress_pct=0,
    )
    db.add(job)
    await db.flush()

    # Dispatch Celery background task
    index_branch_task.delay(branch.id, job.id)
    await db.commit()
    await db.refresh(job)
    return job


@router.get(
    "/{workspace_id}/indexing-jobs",
    response_model=list[IndexingJobResponse],
    summary="List all indexing job statuses for a workspace",
)
async def list_workspace_indexing_jobs(
    workspace_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> list[IndexingJob]:
    """Retrieves all indexing job records for the specified workspace.

    Args:
        workspace_id (int): Target workspace ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        list[IndexingJob]: List of indexing job records.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    res = await db.execute(
        select(IndexingJob)
        .where(IndexingJob.workspace_id == workspace_id)
        .order_by(IndexingJob.created_at.desc())
    )
    return list(res.scalars().all())
