"""API routes for Workspace management and Member operations."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DBSession
from app.model.member import Member
from app.model.user import User
from app.model.workspace import Workspace
from app.schemas.workspace import (
    AddMemberRequest,
    MemberResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


async def get_workspace_or_404(
    workspace_id: int,
    db: AsyncSession,
) -> Workspace:
    """Helper to fetch workspace by ID or raise 404.

    Args:
        workspace_id (int): Target workspace ID.
        db (AsyncSession): Database session.

    Returns:
        Workspace: Retrieved workspace model.

    Raises:
        HTTPException: 404 if workspace does not exist.
    """
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {workspace_id} not found.",
        )
    return workspace


async def check_workspace_access(
    workspace_id: int,
    user_id: int,
    db: AsyncSession,
) -> Workspace:
    """Verifies that user is either owner or member of the workspace.

    Args:
        workspace_id (int): Target workspace ID.
        user_id (int): Current user ID.
        db (AsyncSession): Database session.

    Returns:
        Workspace: Verified workspace model.

    Raises:
        HTTPException: 404 if workspace not found, 403 if unauthorized.
    """
    workspace = await get_workspace_or_404(workspace_id, db)
    if workspace.owner_id == user_id:
        return workspace

    member_res = await db.execute(
        select(Member).where(
            Member.project_id == workspace_id,
            Member.user_id == user_id,
        )
    )
    if member_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this workspace.",
        )
    return workspace


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
@router.post(
    "/",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> Workspace:
    """Creates a new workspace and adds the owner into the member table.

    Args:
        payload (WorkspaceCreate): Workspace creation payload.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        Workspace: Created workspace model.
    """
    workspace = Workspace(
        workspace_name=payload.workspace_name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(workspace)
    await db.flush()

    member = Member(
        project_id=workspace.id,
        user_id=current_user.id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(workspace)

    return workspace


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    summary="List accessible workspaces",
)
@router.get(
    "/",
    response_model=list[WorkspaceResponse],
    summary="List accessible workspaces",
)
async def list_workspaces(
    current_user: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Workspace]:
    """Lists workspaces that current user owns or is a member of.

    Args:
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.
        skip (int, optional): Pagination offset. Defaults to 0.
        limit (int, optional): Pagination limit. Defaults to 100.

    Returns:
        list[Workspace]: Accessible workspaces.
    """
    query = (
        select(Workspace)
        .outerjoin(Member, Workspace.id == Member.project_id)
        .where(
            (Workspace.owner_id == current_user.id)
            | (Member.user_id == current_user.id)
        )
        .distinct()
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace by ID",
)
async def get_workspace(
    workspace_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> Workspace:
    """Retrieves workspace details if user has access.

    Args:
        workspace_id (int): Target workspace ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        Workspace: Workspace object.
    """
    return await check_workspace_access(workspace_id, current_user.id, db)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace details",
)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> Workspace:
    """Updates workspace name and description.

    Args:
        workspace_id (int): Target workspace ID.
        payload (WorkspaceUpdate): Updatable fields.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        Workspace: Updated workspace.
    """
    workspace = await check_workspace_access(workspace_id, current_user.id, db)

    if payload.workspace_name is not None:
        workspace.workspace_name = payload.workspace_name
    if payload.description is not None:
        workspace.description = payload.description

    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
async def delete_workspace(
    workspace_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Deletes a workspace. Only owner is allowed to delete.

    Args:
        workspace_id (int): Target workspace ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Raises:
        HTTPException: 403 if user is not workspace owner.
    """
    workspace = await get_workspace_or_404(workspace_id, db)
    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Only the workspace owner can delete this workspace.",
        )
    await db.delete(workspace)
    await db.commit()


@router.post(
    "/{workspace_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member directly to workspace by email",
)
async def add_member_by_email(
    workspace_id: int,
    payload: AddMemberRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> MemberResponse:
    """Adds a registered user directly as a workspace member by email.

    Args:
        workspace_id (int): Target workspace ID.
        payload (AddMemberRequest): Target user email.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        MemberResponse: Added member information.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    user_res = await db.execute(select(User).where(User.email == payload.email))
    target_user = user_res.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{payload.email}' was not found.",
        )

    existing_member = await db.execute(
        select(Member).where(
            Member.project_id == workspace_id,
            Member.user_id == target_user.id,
        )
    )
    if existing_member.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace.",
        )

    new_member = Member(
        project_id=workspace_id,
        user_id=target_user.id,
    )
    db.add(new_member)
    await db.commit()

    return MemberResponse(
        project_id=workspace_id,
        user_id=target_user.id,
        email=target_user.email,
        username=target_user.username,
    )


@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberResponse],
    summary="List workspace members",
)
async def list_workspace_members(
    workspace_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> list[MemberResponse]:
    """Lists all members of a workspace.

    Args:
        workspace_id (int): Target workspace ID.
        current_user (CurrentUser): Authenticated user.
        db (DBSession): Database session.

    Returns:
        list[MemberResponse]: List of workspace members.
    """
    await check_workspace_access(workspace_id, current_user.id, db)

    result = await db.execute(
        select(Member)
        .where(Member.project_id == workspace_id)
        .options(selectinload(Member.user))
    )
    members = result.scalars().all()
    return [
        MemberResponse(
            project_id=m.project_id,
            user_id=m.user_id,
            email=m.user.email if m.user else None,
            username=m.user.username if m.user else None,
        )
        for m in members
    ]
