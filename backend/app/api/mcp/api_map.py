from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import CurrentAgent
from app.core import APIResponse, ErrorCode, ResponseSuccessSchema, build_error_docs
from app.engine.graph.service import GraphServiceDep

router = APIRouter(prefix="/api-map", tags=["API Map"])


class ApiEndpointResponse(BaseModel):
    id: str
    protocol: str
    signature: str | None
    framework: str | None
    file_id: str | None
    file_path: str | None
    handler_node_id: str | None
    handler_name: str | None
    start_line: int | None
    """1-based line of the handler node."""
    caller_count: int
    details: dict[str, Any]
    """Protocol-specific fields, e.g. REST: ``http_method``, ``path``, ``path_params``."""
    metadata: dict[str, Any]


class ApiCallResponse(BaseModel):
    id: str
    protocol: str
    signature: str | None
    library: str | None
    target_hint: str | None
    is_dynamic: bool
    file_id: str | None
    file_path: str | None
    call_node_id: str | None
    scope: str | None
    start_line: int | None
    """1-based line of the call node."""
    targets: list[dict[str, Any]]
    """Endpoints the call resolves to: ``endpoint_id``, ``project_id``, ``signature``,
    ``rule``, ``confidence``. Empty when unresolved."""
    details: dict[str, Any]
    """Protocol-specific fields, e.g. REST: ``http_method``, ``path``."""
    metadata: dict[str, Any]


@router.get(
    "/projects/{project_id}/endpoints",
    summary="List API endpoints served by a project",
    response_model=ResponseSuccessSchema[list[ApiEndpointResponse]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_project_endpoints(
    project_id: int, graph_service: GraphServiceDep, user: CurrentAgent
) -> APIResponse:
    return APIResponse.ok(graph_service.list_api_endpoints_in_project(project_id))


@router.get(
    "/projects/{project_id}/calls",
    summary="List API calls made by a project",
    response_model=ResponseSuccessSchema[list[ApiCallResponse]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_project_calls(
    project_id: int, graph_service: GraphServiceDep, user: CurrentAgent
) -> APIResponse:
    return APIResponse.ok(graph_service.list_api_calls_in_project(project_id))
