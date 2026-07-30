from fastapi import APIRouter

from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
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
from app.services.branch_service import BranchServiceDep

router = APIRouter(prefix="/branches", tags=["Branch"])


@router.post(
    "/remote-branches",
    response_model=ResponseSuccessSchema[RemoteBranchesResponse],
    responses=build_error_docs(
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List all remote branches of a repository using git_url",
)
async def inspect_remote_branches(
    payload: InspectGitHubBranchesRequest,
    branch_service: BranchServiceDep,
) -> APIResponse:
    data = await branch_service.inspect_remote_branches(payload)
    return APIResponse.ok(data=data)


@router.get(
    "/{workspace_id}/workspace-branches",
    response_model=ResponseSuccessSchema[list[BranchResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List registered branches in workspace",
)
async def list_workspace_branches(
    workspace_id: int,
    branch_service: BranchServiceDep,
    repository_id: int | None = None,
) -> APIResponse:
    data = await branch_service.list_workspace_branches(
        workspace_id, repository_id=repository_id
    )
    return APIResponse.ok(data=data)


@router.post(
    "/{workspace_id}/repositories",
    response_model=ResponseSuccessSchema[RepositoryResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Attach repository and register branches",
)
async def attach_repository(
    workspace_id: int,
    payload: RepositoryCreateRequest,
    branch_service: BranchServiceDep,
) -> APIResponse:
    data = await branch_service.attach_repository(workspace_id, payload)
    return APIResponse.ok(data=data)


@router.post(
    "/{workspace_id}/{branch_id}/projects",
    response_model=ResponseSuccessSchema[ProjectResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Configure sub-project under branch",
)
async def create_or_config_subproject(
    workspace_id: int,
    branch_id: int,
    payload: ProjectCreateRequest,
    branch_service: BranchServiceDep,
) -> APIResponse:
    data = await branch_service.create_or_config_subproject(
        workspace_id, branch_id, payload
    )
    return APIResponse.ok(data=data)


@router.get(
    "/{workspace_id}/hierarchy",
    response_model=ResponseSuccessSchema[WorkspaceHierarchyResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get full hierarchy tree of workspace",
)
async def get_workspace_hierarchy(
    workspace_id: int,
    branch_service: BranchServiceDep,
) -> APIResponse:
    data = await branch_service.get_workspace_hierarchy(workspace_id)
    return APIResponse.ok(data=data)


@router.patch(
    "/{workspace_id}/projects/{project_id}",
    response_model=ResponseSuccessSchema[ProjectResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Update sub-project config",
)
async def update_subproject(
    workspace_id: int,
    project_id: int,
    payload: ProjectUpdateRequest,
    branch_service: BranchServiceDep,
) -> APIResponse:
    data = await branch_service.update_subproject(workspace_id, project_id, payload)
    return APIResponse.ok(data=data)


@router.delete(
    "/{workspace_id}/projects/{project_id}",
    response_model=ResponseSuccessSchema[None],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Delete sub-project",
)
async def delete_subproject(
    workspace_id: int,
    project_id: int,
    branch_service: BranchServiceDep,
) -> APIResponse:
    await branch_service.delete_subproject(workspace_id, project_id)
    return APIResponse.ok(message="Sub-project deleted successfully")


@router.delete(
    "/{workspace_id}/{branch_id}",
    response_model=ResponseSuccessSchema[None],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Unlink branch from workspace",
)
async def remove_branch_from_workspace(
    workspace_id: int,
    branch_id: int,
    branch_service: BranchServiceDep,
) -> APIResponse:
    await branch_service.remove_branch_from_workspace(workspace_id, branch_id)
    return APIResponse.ok(message="Branch removed from workspace successfully")


@router.delete(
    "/{workspace_id}/repositories/{repository_id}",
    response_model=ResponseSuccessSchema[None],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Delete repository from workspace",
)
async def remove_repository_from_workspace(
    workspace_id: int,
    repository_id: int,
    branch_service: BranchServiceDep,
) -> APIResponse:
    await branch_service.remove_repository_from_workspace(workspace_id, repository_id)
    return APIResponse.ok(message="Repository removed from workspace successfully")
