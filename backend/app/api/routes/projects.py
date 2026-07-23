"""API routes for Project management, Members, and Repository links."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, DBSession
from app.domain.project import Project
from app.domain.member import Member
from app.domain.user import User
from app.domain.repository import Repository
from app.enums.member_role import MemberRole

from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
)
from app.schemas.member import MemberInviteRequest, MemberResponse
from app.schemas.repository import RepositoryLinkCreate, RepositoryLinkResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


async def check_project_access(
    project_id: int,
    user_id: int,
    db: AsyncSession,
    required_roles: list[MemberRole] | None = None,
) -> Project:
    """Verifies that a user has access to a project and holds a required role.

    If the user is the project owner, they are granted full privileges.

    Args:
        project_id: Target project ID.
        user_id: Current user ID.
        db: Database session.
        required_roles: Roles allowed to perform the action.

    Returns:
        Project: The retrieved project instance.

    Raises:
        HTTPException: 404 if project doesn't exist, 403 if unauthorized.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    if project.owner_id == user_id:
        return project

    member_res = await db.execute(
        select(Member).where(Member.project_id == project_id, Member.user_id == user_id)
    )
    member = member_res.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this project.",
        )

    if required_roles and member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Insufficient role privileges.",
        )

    return project


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    payload: ProjectCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> Project:
    """Creates a project and registers the owner as an Admin member.

    Args:
        payload: Project creation details.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        Project: Created project database object.
    """
    project = Project(
        project_name=payload.project_name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(project)
    await db.flush()

    member = Member(
        project_id=project.id,
        user_id=current_user.id,
        role=MemberRole.ADMIN,
    )
    db.add(member)
    await db.commit()
    await db.refresh(project)

    return project


@router.get(
    "/",
    response_model=list[ProjectResponse],
    summary="List all accessible projects",
)
async def list_projects(
    current_user: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Project]:
    """Lists projects that the current user owns or is a member of.

    Args:
        current_user: Currently authenticated user.
        db: Database session.
        skip: Pagination offset.
        limit: Pagination limit.

    Returns:
        list[Project]: List of accessible projects.
    """
    query = (
        select(Project)
        .outerjoin(Member, Project.id == Member.project_id)
        .where(
            (Project.owner_id == current_user.id) | (Member.user_id == current_user.id)
        )
        .distinct()
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get project details with members and repositories",
)
async def get_project(
    project_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> Project:
    """Retrieves project details, loading member and repository details.

    Args:
        project_id: Target project ID.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        Project: Detailed project object.
    """
    await check_project_access(project_id, current_user.id, db)

    query = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.members).selectinload(Member.user),
            selectinload(Project.repositories),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one()
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project metadata",
)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> Project:
    """Updates the project name or description.

    Args:
        project_id: Target project ID.
        payload: Updatable fields.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        Project: Updated project.
    """
    project = await check_project_access(
        project_id, current_user.id, db, required_roles=[MemberRole.ADMIN]
    )

    if payload.project_name is not None:
        project.project_name = payload.project_name
    if payload.description is not None:
        project.description = payload.description

    await db.commit()
    await db.refresh(project)
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a project",
)
async def delete_project(
    project_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> dict[str, str]:
    """Deletes a project. Only the project owner is permitted to perform this.

    Args:
        project_id: Target project ID.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        dict[str, str]: Action completion message.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Only the project owner can delete this project.",
        )

    await db.delete(project)
    await db.commit()
    return {"message": "Project successfully deleted."}


# --- Project Members ---


@router.post(
    "/{project_id}/members/invite",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a member by email",
)
async def invite_member(
    project_id: int,
    payload: MemberInviteRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> Member:
    """Invites a user to a project using their email.

    Args:
        project_id: Target project ID.
        payload: Invitation details.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        Member: Created member database record.
    """
    await check_project_access(
        project_id, current_user.id, db, required_roles=[MemberRole.ADMIN]
    )

    user_res = await db.execute(select(User).where(User.email == payload.email))
    invited_user = user_res.scalar_one_or_none()
    if not invited_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{payload.email}' is not registered in the system.",
        )

    member_check = await db.execute(
        select(Member).where(
            Member.project_id == project_id, Member.user_id == invited_user.id
        )
    )
    if member_check.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project.",
        )

    new_member = Member(
        project_id=project_id,
        user_id=invited_user.id,
        role=payload.role,
    )
    db.add(new_member)
    await db.commit()

    final_res = await db.execute(
        select(Member)
        .where(Member.id == new_member.id)
        .options(selectinload(Member.user))
    )
    return final_res.scalar_one()


@router.get(
    "/{project_id}/members",
    response_model=list[MemberResponse],
    summary="List all project members",
)
async def list_members(
    project_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> list[Member]:
    """Retrieves all members currently belonging to the project.

    Args:
        project_id: Target project ID.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        list[Member]: List of members.
    """
    await check_project_access(project_id, current_user.id, db)

    query = (
        select(Member)
        .where(Member.project_id == project_id)
        .options(selectinload(Member.user))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a member from the project",
)
async def remove_member(
    project_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> dict[str, str]:
    """Removes a member from the project.

    Args:
        project_id: Target project ID.
        user_id: ID of user to remove.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        dict[str, str]: Action completion message.
    """
    project = await check_project_access(
        project_id, current_user.id, db, required_roles=[MemberRole.ADMIN]
    )

    if user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner of the project. Delete the project to remove.",
        )

    member_res = await db.execute(
        select(Member).where(Member.project_id == project_id, Member.user_id == user_id)
    )
    member = member_res.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this project.",
        )

    await db.delete(member)
    await db.commit()
    return {"message": "Member successfully removed from project."}


# --- Project Repositories ---


@router.post(
    "/{project_id}/repositories",
    response_model=RepositoryLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a repository link to a project",
)
async def attach_repository(
    project_id: int,
    payload: RepositoryLinkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> Repository:
    """Attaches a Git repository link to the project with a 'pending' status.

    Args:
        project_id: Target project ID.
        payload: Repository metadata details.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        Repository: Created repository database object.
    """
    await check_project_access(
        project_id,
        current_user.id,
        db,
        required_roles=[MemberRole.ADMIN, MemberRole.DEVELOPER],
    )

    new_repo = Repository(
        project_id=project_id,
        name=payload.name,
        git_url=payload.git_url,
        description=payload.description,
        default_branch=payload.default_branch,
        status="pending",
    )
    db.add(new_repo)
    await db.commit()
    await db.refresh(new_repo)

    return new_repo


@router.get(
    "/{project_id}/repositories",
    response_model=list[RepositoryLinkResponse],
    summary="List all repository links in a project",
)
async def list_repositories(
    project_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> list[Repository]:
    """Lists all repositories linked to the specified project.

    Args:
        project_id: Target project ID.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        list[Repository]: List of repository link structures.
    """
    await check_project_access(project_id, current_user.id, db)

    result = await db.execute(
        select(Repository).where(Repository.project_id == project_id)
    )
    return list(result.scalars().all())


@router.delete(
    "/{project_id}/repositories/{repository_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a repository link from the project",
)
async def remove_repository(
    project_id: int,
    repository_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> dict[str, str]:
    """Detaches and deletes a Git repository link from the project.

    Args:
        project_id: Target project ID.
        repository_id: ID of repository to detach.
        current_user: Currently authenticated user.
        db: Database session.

    Returns:
        dict[str, str]: Action completion message.
    """
    await check_project_access(
        project_id, current_user.id, db, required_roles=[MemberRole.ADMIN]
    )

    repo_res = await db.execute(
        select(Repository).where(
            Repository.project_id == project_id, Repository.id == repository_id
        )
    )
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository link not found in this project.",
        )

    await db.delete(repo)
    await db.commit()
    return {"message": "Repository link successfully removed from project."}
