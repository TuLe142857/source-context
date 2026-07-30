"""Service module for workspace operations."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DBSession
from app.core import AppException, ErrorCode
from app.model import Member, User, Workspace
from app.schemas.workspace import MemberResponse


class WorkspaceService:
    """Service for managing workspace CRUD and membership operations."""

    def __init__(self, session: DBSession, current_user: CurrentUser) -> None:
        """Initializes WorkspaceService with database session and authenticated user.

        Args:
            session (DBSession): Async database session.
            current_user (CurrentUser): Authenticated user context.
        """
        self.session = session
        self.current_user = current_user

    async def _get_workspace_or_raise(self, workspace_id: int) -> Workspace:
        """Helper to fetch workspace by ID or raise RESOURCE_NOT_FOUND.

        Args:
            workspace_id (int): Target workspace ID.

        Returns:
            Workspace: Found workspace entity.

        Raises:
            AppException: 404 if workspace does not exist.
        """
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.session.scalars(stmt)
        workspace = result.one_or_none()
        if workspace is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Workspace not found",
            )
        return workspace

    async def _check_workspace_access(self, workspace_id: int) -> Workspace:
        """Verifies that current user is owner or member of the workspace.

        Args:
            workspace_id (int): Target workspace ID.

        Returns:
            Workspace: Verified workspace model.

        Raises:
            AppException: 404 if workspace not found, 403 if user lacks access.
        """
        workspace = await self._get_workspace_or_raise(workspace_id)
        if workspace.owner_id == self.current_user.id:
            return workspace

        stmt = select(Member).where(
            Member.workspace_id == workspace_id,
            Member.user_id == self.current_user.id,
        )
        result = await self.session.scalars(stmt)
        member = result.one_or_none()
        if member is None:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="You do not have access to this workspace",
            )
        return workspace

    async def get_accessible_workspace(self) -> list[Workspace]:
        """Retrieves all workspaces accessible by the current user.

        Returns:
            list[Workspace]: List of accessible workspaces.
        """
        stmt = (
            select(Workspace)
            .join(Member, Workspace.id == Member.workspace_id)
            .join(User, User.id == Member.user_id)
            .where(User.id == self.current_user.id)
            .distinct()
        )

        results = await self.session.scalars(stmt)
        workspaces = list(results.all())
        return workspaces

    async def create_workspace(
        self, workspace_name: str, description: str | None = None
    ) -> Workspace:
        """Creates a new workspace and adds current user as a member.

        Args:
            workspace_name (str): Name of the new workspace.
            description (str | None, optional): Optional description. Defaults to None.

        Returns:
            Workspace: Created workspace entity.

        Raises:
            AppException: 409 if a workspace with the same name owned by user exists.
        """
        stmt = select(Workspace).where(
            Workspace.owner_id == self.current_user.id,
            Workspace.workspace_name == workspace_name,
        )

        result = await self.session.scalars(stmt)
        existing_workspace = result.one_or_none()

        if existing_workspace is not None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                message="Workspace already exists",
            )

        new_workspace = Workspace(
            workspace_name=workspace_name,
            description=description,
            owner_id=self.current_user.id,
        )

        self.session.add(new_workspace)
        await self.session.flush()

        new_member = Member(user_id=self.current_user.id, workspace_id=new_workspace.id)
        self.session.add(new_member)
        await self.session.commit()
        await self.session.refresh(new_workspace)

        return new_workspace

    async def get_workspace_by_id(self, workspace_id: int) -> Workspace:
        """Retrieves workspace by ID if accessible by current user.

        Args:
            workspace_id (int): Target workspace ID.

        Returns:
            Workspace: Found workspace entity.

        Raises:
            AppException: 404 if workspace not found, 403 if access denied.
        """
        return await self._check_workspace_access(workspace_id)

    async def delete_workspace(self, workspace_id: int) -> None:
        """Deletes a workspace. Only workspace owner is permitted.

        Args:
            workspace_id (int): Workspace ID to delete.

        Raises:
            AppException: 404 if not found, 403 if user is not owner.
        """
        workspace = await self._get_workspace_or_raise(workspace_id)
        if workspace.owner_id != self.current_user.id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Only the workspace owner can delete this workspace",
            )
        await self.session.delete(workspace)
        await self.session.commit()

    async def add_member(
        self, workspace_id: int, email: str | None = None, user_id: int | None = None
    ) -> MemberResponse:
        """Adds a member to a workspace by email or user ID.

        Args:
            workspace_id (int): Target workspace ID.
            email (str | None, optional): User email. Defaults to None.
            user_id (int | None, optional): User ID. Defaults to None.

        Returns:
            MemberResponse: Added member information.

        Raises:
            AppException: If workspace not found, forbidden, user not found, or user already a member.
        """
        await self._check_workspace_access(workspace_id)

        if email is not None:
            user_stmt = select(User).where(User.email == email)
        elif user_id is not None:
            user_stmt = select(User).where(User.id == user_id)
        else:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Either email or user_id must be provided",
            )

        user_result = await self.session.scalars(user_stmt)
        target_user = user_result.one_or_none()
        if target_user is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User not found",
            )

        member_stmt = select(Member).where(
            Member.workspace_id == workspace_id,
            Member.user_id == target_user.id,
        )
        member_result = await self.session.scalars(member_stmt)
        if member_result.one_or_none() is not None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                message="User is already a member of this workspace",
            )

        new_member = Member(workspace_id=workspace_id, user_id=target_user.id)
        self.session.add(new_member)
        await self.session.commit()

        return MemberResponse(
            workspace_id=workspace_id,
            project_id=workspace_id,
            user_id=target_user.id,
            email=target_user.email,
            username=target_user.username,
            full_name=target_user.full_name,
        )

    async def get_workspace_members(self, workspace_id: int) -> list[MemberResponse]:
        """Lists all members of a workspace.

        Args:
            workspace_id (int): Target workspace ID.

        Returns:
            list[MemberResponse]: List of workspace members.

        Raises:
            AppException: If workspace not found or access denied.
        """
        await self._check_workspace_access(workspace_id)

        stmt = (
            select(Member)
            .options(selectinload(Member.user))
            .where(Member.workspace_id == workspace_id)
        )
        result = await self.session.scalars(stmt)
        members = list(result.all())

        return [
            MemberResponse(
                workspace_id=m.workspace_id,
                project_id=m.workspace_id,
                user_id=m.user_id,
                email=m.user.email if m.user else None,
                username=m.user.username if m.user else None,
                full_name=m.user.full_name if m.user else None,
            )
            for m in members
        ]

    async def remove_member(self, workspace_id: int, target_user_id: int) -> None:
        """Removes a member from a workspace.

        Args:
            workspace_id (int): Target workspace ID.
            target_user_id (int): ID of user to remove.

        Raises:
            AppException: If workspace not found, owner tries to be removed, permission denied, or member not found.
        """
        workspace = await self._get_workspace_or_raise(workspace_id)

        if target_user_id == workspace.owner_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Cannot remove workspace owner",
            )

        if (
            self.current_user.id != workspace.owner_id
            and self.current_user.id != target_user_id
        ):
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Only workspace owner or the user themselves can remove a member",
            )

        stmt = select(Member).where(
            Member.workspace_id == workspace_id,
            Member.user_id == target_user_id,
        )
        result = await self.session.scalars(stmt)
        member = result.one_or_none()
        if member is None:
            raise AppException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Member not found in workspace",
            )

        await self.session.delete(member)
        await self.session.commit()


def get_workspace_service(
    current_user: CurrentUser, session: DBSession
) -> WorkspaceService:
    """Dependency provider for WorkspaceService.

    Args:
        current_user (CurrentUser): Authenticated user.
        session (DBSession): Async database session.

    Returns:
        WorkspaceService: Initialized WorkspaceService instance.
    """
    return WorkspaceService(session=session, current_user=current_user)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
