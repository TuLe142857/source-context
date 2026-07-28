from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from app.graph.query import GraphQuery
from app.graph.model import UASTNodeModel
from app.core import APIResponse, ResponseSuccessSchema, AppException, ErrorCode
from app.api.dependencies import CurrentAgent, CurrentAgentOrNone

router = APIRouter(prefix="/graph", tags=["Graph Query"])


class FileStructureNode(BaseModel):
    id: str
    name: str | None
    type: str | None
    children: list["FileStructureNode"] = []


class NodeInfo(BaseModel):
    id: str
    name: str | None
    file_id: str | None


@router.get(
    "/projects/{project_id}/files",
    summary="Get files in project",
    response_model=ResponseSuccessSchema[list[tuple[str, str]]],
)
async def get_files(
    user: CurrentAgent,
    project_id: int,
):
    results: list[tuple[str, str]] | None = await run_in_threadpool(
        GraphQuery.list_files_in_projects, project_id
    )
    return APIResponse.ok(results)


@router.get(
    "/files/{file_id}/structures",
    response_model=ResponseSuccessSchema[list[FileStructureNode] | None],
)
async def get_file_structures(
    user: CurrentAgent,
    file_id: str,
):
    res = await run_in_threadpool(GraphQuery.get_file_structure, file_id)
    return APIResponse.ok(res)


@router.get(
    "/files/{file_id}/contents",
    summary="Get contents of file",
    response_model=ResponseSuccessSchema[str | None],
)
async def get_file_contents(
    user: CurrentAgent,
    file_id: str,
):
    result = await run_in_threadpool(GraphQuery.get_file_content, file_id)
    return APIResponse.ok(result)


@router.get(
    "/nodes/{node_id}",
    response_model=ResponseSuccessSchema[NodeInfo],
)
async def get_node_info(
    user: CurrentAgent,
    node_id: str,
):
    node: UASTNodeModel = await run_in_threadpool(GraphQuery.get_node, node_id)
    return APIResponse.ok(
        {"id": node.uid, "name": node.name, "file_id": node.file_node_uid}
    )


@router.get(
    "/nodes/{node_id}/content",
    summary="Get node's source code as string",
    response_model=ResponseSuccessSchema[str | None],
)
async def get_node_content(
    user: CurrentAgent,
    node_id: str,
):
    results = await run_in_threadpool(GraphQuery.get_node_content, node_id)
    return APIResponse.ok(results)


@router.get(
    "/nodes/{node_id}/usage",
    response_model=ResponseSuccessSchema[list[str] | None],
)
async def check_node_usages(
    user: CurrentAgent,
    node_id: str,
):
    results: list[str] = await run_in_threadpool(GraphQuery.find_usage, node_id)
    return APIResponse.ok(results)


@router.get(
    "/nodes/{node_id}/calleees}",
    response_model=ResponseSuccessSchema[list[str] | None],
)
async def get_node_callees(
    user: CurrentAgent,
    node_id: str,
):
    results = await run_in_threadpool(GraphQuery.find_callees, node_id)
    return APIResponse.ok(results)
