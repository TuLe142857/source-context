from fastapi import APIRouter

from app.api.dependencies import VectorServiceDep
from app.core import (
    APIResponse,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.retrieval.retriever import QueryResult
from app.schemas.vector import VectorSearchRequest

router = APIRouter(prefix="/vector", tags=["Vector"])


@router.post(
    "/search/{repository_id}/{branch_name}",
    response_model=ResponseSuccessSchema[list[QueryResult]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Search code chunks within a specific repository branch",
)
async def search_cross_repository(
    repository_id: int,
    branch_name: str,
    request: VectorSearchRequest,
    vector_service: VectorServiceDep,
) -> APIResponse:
    results = await vector_service.search_with_branch_filter(
        repository_id=repository_id,
        branch_name=branch_name,
        query=request.query,
        top_k=request.top_k,
    )
    return APIResponse.ok(data=results)


@router.post(
    "/search/{workspace_id}",
    response_model=ResponseSuccessSchema[list[QueryResult]],
    responses=build_error_docs(
        ErrorCode.RESOURCE_NOT_FOUND,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.UNKNOWN_ERROR,
    ),
    summary="Search code chunks across a workspace",
)
async def search_workspace(
    workspace_id: int,
    request: VectorSearchRequest,
    vector_service: VectorServiceDep,
) -> APIResponse:
    results = await vector_service.search(
        workspace_id=workspace_id,
        query=request.query,
        top_k=request.top_k,
    )
    return APIResponse.ok(data=results)
