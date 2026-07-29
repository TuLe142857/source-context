"""MCP general router endpoints."""

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentAgent, DBSession
from app.model.branch import Branch
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.model.workspace_branch import WorkspaceBranch
from app.model.workspace_repository import WorkspaceRepository
from app.schemas.branch import SimpleBranchResponse
from app.schemas.repository import SimpleRepositoryResponse
from app.schemas.workspace import WorkspaceResponse

router = APIRouter(prefix="/general", tags=["General"])


@dataclass
class RepositoryRequest:
    """Request payload for fetching workspace repositories."""

    workspace_id: int


@dataclass
class BranchRequest:
    """Request payload for fetching repository branches within a workspace."""

    workspace_id: int
    repository_id: int


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def get_workspaces(user: CurrentAgent, session: DBSession) -> list[Workspace]:
    stmt = select(Workspace).where(Workspace.owner_id == user.id)
    results = await session.scalars(stmt)
    return list(results.all())


@router.post("/repositories", response_model=list[SimpleRepositoryResponse])
async def get_repositories(
    user: CurrentAgent, session: DBSession, payload: RepositoryRequest
) -> list[Repository]:
    stmt = (
        select(Repository)
        .join(WorkspaceRepository, Repository.id == WorkspaceRepository.repository_id)
        .join(Workspace, Workspace.id == WorkspaceRepository.workspace_id)
        .where(Workspace.id == payload.workspace_id)
    )

    results = await session.scalars(stmt)
    return list(results.all())


@router.post("/branches", response_model=list[SimpleBranchResponse])
async def get_branches(
    user: CurrentAgent, session: DBSession, payload: BranchRequest
) -> list[Branch]:
    stmt = (
        select(Branch)
        .join(WorkspaceBranch, Branch.id == WorkspaceBranch.branch_id)
        .where(
            WorkspaceBranch.workspace_id == payload.workspace_id,
            Branch.repository_id == payload.repository_id,
        )
    )

    results = await session.scalars(stmt)
    return list(results.all())
