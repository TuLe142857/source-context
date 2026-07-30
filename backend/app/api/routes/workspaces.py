from fastapi import APIRouter

from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.schemas.workspace import (
    AddMemberRequest,
    CreateWorkspaceRequest,
    MemberResponse,
    WorkspaceResponse,
)
from app.services.workspace_service import WorkspaceServiceDep

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get(
    "",
    response_model=ResponseSuccessSchema[list[WorkspaceResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List accessible workspaces",
)
async def get_accessible_workspace(
    workspace_service: WorkspaceServiceDep,
) -> APIResponse:
    workspaces = await workspace_service.get_accessible_workspace()
    return APIResponse.ok(data=workspaces)


@router.post(
    "",
    response_model=ResponseSuccessSchema[WorkspaceResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_ALREADY_EXISTS,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Create a workspace",
)
async def create_workspace(
    workspace_service: WorkspaceServiceDep,
    payload: CreateWorkspaceRequest,
) -> APIResponse:
    workspace = await workspace_service.create_workspace(
        workspace_name=payload.workspace_name,
        description=payload.description,
    )
    return APIResponse.ok(data=workspace)


@router.get(
    "/{workspace_id}",
    response_model=ResponseSuccessSchema[WorkspaceResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get workspace by ID",
)
async def get_workspace_by_id(
    workspace_id: int,
    workspace_service: WorkspaceServiceDep,
) -> APIResponse:
    workspace = await workspace_service.get_workspace_by_id(workspace_id=workspace_id)
    return APIResponse.ok(data=workspace)


@router.delete(
    "/{workspace_id}",
    response_model=ResponseSuccessSchema[None],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Delete workspace",
)
async def delete_workspace(
    workspace_id: int,
    workspace_service: WorkspaceServiceDep,
) -> APIResponse:
    await workspace_service.delete_workspace(workspace_id=workspace_id)
    return APIResponse.ok(message="Workspace deleted successfully")


@router.post(
    "/{workspace_id}/members",
    response_model=ResponseSuccessSchema[MemberResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.RESOURCE_ALREADY_EXISTS,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Add member to workspace",
)
async def add_member(
    workspace_id: int,
    payload: AddMemberRequest,
    workspace_service: WorkspaceServiceDep,
) -> APIResponse:
    member_data = await workspace_service.add_member(
        workspace_id=workspace_id,
        email=payload.email,
        user_id=payload.user_id,
    )
    return APIResponse.ok(data=member_data)


@router.get(
    "/{workspace_id}/members",
    response_model=ResponseSuccessSchema[list[MemberResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List workspace members",
)
async def get_workspace_members(
    workspace_id: int,
    workspace_service: WorkspaceServiceDep,
) -> APIResponse:
    members = await workspace_service.get_workspace_members(workspace_id=workspace_id)
    return APIResponse.ok(data=members)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    response_model=ResponseSuccessSchema[None],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Remove member from workspace",
)
async def remove_member(
    workspace_id: int,
    user_id: int,
    workspace_service: WorkspaceServiceDep,
) -> APIResponse:
    await workspace_service.remove_member(
        workspace_id=workspace_id,
        target_user_id=user_id,
    )
    return APIResponse.ok(message="Member removed successfully")
