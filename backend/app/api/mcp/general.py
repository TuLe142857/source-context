from fastapi import APIRouter

from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.schemas.branch import SimpleBranchResponse
from app.schemas.general import (
    BranchProjectsRequest,
    BranchRequest,
    RepositoryRequest,
)
from app.schemas.project import ProjectResponse
from app.schemas.repository import SimpleRepositoryResponse
from app.schemas.workspace import WorkspaceResponse
from app.services.general_service import GeneralServiceDep

router = APIRouter(prefix="/general", tags=["General"])


@router.get(
    "/workspaces",
    response_model=ResponseSuccessSchema[list[WorkspaceResponse]],
    responses=build_error_docs(
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get user workspaces",
)
async def get_workspaces(
    general_service: GeneralServiceDep,
) -> APIResponse:
    workspaces = await general_service.get_workspaces()
    return APIResponse.ok(data=workspaces)


@router.post(
    "/repositories",
    response_model=ResponseSuccessSchema[list[SimpleRepositoryResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get workspace repositories",
)
async def get_repositories(
    payload: RepositoryRequest,
    general_service: GeneralServiceDep,
) -> APIResponse:
    repos = await general_service.get_repositories(payload.workspace_id)
    return APIResponse.ok(data=repos)


@router.post(
    "/branches",
    response_model=ResponseSuccessSchema[list[SimpleBranchResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get workspace repository branches",
)
async def get_branches(
    payload: BranchRequest,
    general_service: GeneralServiceDep,
) -> APIResponse:
    branches = await general_service.get_branches(
        workspace_id=payload.workspace_id,
        repository_id=payload.repository_id,
    )
    return APIResponse.ok(data=branches)


@router.post(
    "/projects",
    response_model=ResponseSuccessSchema[list[ProjectResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get sub-projects of a branch in a workspace",
)
async def get_projects(
    payload: BranchProjectsRequest,
    general_service: GeneralServiceDep,
) -> APIResponse:
    projects = await general_service.get_projects(
        workspace_id=payload.workspace_id,
        repo_id=payload.repo_id,
        branch_name=payload.branch_name,
    )
    return APIResponse.ok(data=projects)
