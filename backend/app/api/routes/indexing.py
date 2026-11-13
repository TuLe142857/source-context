from fastapi import APIRouter

from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.schemas.indexing import (
    IndexingJobResponse,
    IndexingRunResponse,
    IndexingStateResponse,
)
from app.services.indexing_service import IndexingServiceDep

router = APIRouter(prefix="/indexing", tags=["Indexing"])


@router.post(
    "/{workspace_id}/branch/{branch_id}",
    response_model=ResponseSuccessSchema[IndexingJobResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.ACTION_CONFLICT,
        ErrorCode.ACTION_ALREADY_PERFORMED,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Trigger indexing for a single branch",
)
async def trigger_branch_indexing(
    workspace_id: int,
    branch_id: int,
    indexing_service: IndexingServiceDep,
    force_full: bool = False,
) -> APIResponse:
    data = await indexing_service.trigger_branch_indexing(
        workspace_id, branch_id, force_full=force_full
    )
    return APIResponse.ok(data=data)


@router.post(
    "/{workspace_id}",
    response_model=ResponseSuccessSchema[list[IndexingJobResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.BAD_REQUEST,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Trigger indexing for all branches in workspace",
)
async def trigger_workspace_indexing(
    workspace_id: int,
    indexing_service: IndexingServiceDep,
    force_full: bool = False,
) -> APIResponse:
    data = await indexing_service.trigger_workspace_indexing(
        workspace_id, force_full=force_full
    )
    return APIResponse.ok(data=data)


@router.get(
    "/{workspace_id}/jobs",
    response_model=ResponseSuccessSchema[list[IndexingJobResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List indexing jobs for workspace",
)
async def list_workspace_indexing_jobs(
    workspace_id: int,
    indexing_service: IndexingServiceDep,
) -> APIResponse:
    data = await indexing_service.list_workspace_indexing_jobs(workspace_id)
    return APIResponse.ok(data=data)


@router.get(
    "/{workspace_id}/runs",
    response_model=ResponseSuccessSchema[list[IndexingRunResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List indexing runs for workspace",
)
async def list_workspace_indexing_runs(
    workspace_id: int,
    indexing_service: IndexingServiceDep,
) -> APIResponse:
    data = await indexing_service.list_workspace_indexing_runs(workspace_id)
    return APIResponse.ok(data=data)


@router.get(
    "/{workspace_id}/states",
    response_model=ResponseSuccessSchema[list[IndexingStateResponse]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="List indexing checkpoints for workspace branches",
)
async def list_workspace_indexing_states(
    workspace_id: int,
    indexing_service: IndexingServiceDep,
) -> APIResponse:
    data = await indexing_service.list_workspace_indexing_states(workspace_id)
    return APIResponse.ok(data=data)


@router.get(
    "/{workspace_id}/runs/{run_id}",
    response_model=ResponseSuccessSchema[IndexingRunResponse],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.FORBIDDEN,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Get one indexing run",
)
async def get_workspace_indexing_run(
    workspace_id: int,
    run_id: int,
    indexing_service: IndexingServiceDep,
) -> APIResponse:
    data = await indexing_service.get_workspace_indexing_run(workspace_id, run_id)
    return APIResponse.ok(data=data)
