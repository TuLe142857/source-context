from fastapi import APIRouter
from pydantic import BaseModel
from app.graph.service import GraphServiceDep
from app.core import APIResponse, ResponseSuccessSchema, build_error_docs, ErrorCode
from app.api.dependencies import CurrentAgent


router = APIRouter(prefix="/graph", tags=["Graph Query"])


class FileInfo(BaseModel):
    id: str
    path: str


class FileStructureNode(BaseModel):
    id: str
    name: str | None
    type: str | None
    children: list["FileStructureNode"] = []


class NodeInfo(BaseModel):
    id: str
    name: str | None
    file_id: str | None


class UastNodeSchema(BaseModel):
    id: str
    name: str | None
    file_id: str
    start_byte: int
    end_byte: int
    start_point: tuple[int, int]
    end_point: tuple[int, int]


@router.get(
    "/projects/{project_id}/files",
    summary="Get files in project",
    response_model=ResponseSuccessSchema[list[FileInfo]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_files(
    project_id: int,
    graph_service: GraphServiceDep,
    user: CurrentAgent,
):
    res = [
        FileInfo(path=_[0], id=_[1])
        for _ in graph_service.list_files_in_projects(project_id)
    ]
    return APIResponse.ok(res)


@router.get(
    "/files/{file_id}/structure",
    response_model=ResponseSuccessSchema[list[FileStructureNode]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_file_structure(
    file_id: str,
    graph_service: GraphServiceDep,
    user: CurrentAgent,
):
    res = graph_service.get_file_structure(file_id)
    return APIResponse.ok(res)


@router.get(
    "/files/{file_id}/content",
    summary="Get contents of file",
    response_model=ResponseSuccessSchema[str | None],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_file_contents(
    file_id: str,
    graph_service: GraphServiceDep,
    user: CurrentAgent,
):
    res = graph_service.get_file_content(file_id)
    return APIResponse.ok(res)


@router.get(
    "/nodes/{node_id}",
    response_model=ResponseSuccessSchema[UastNodeSchema],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_node_info(node_id: str, graph_service: GraphServiceDep, user: CurrentAgent):
    node = graph_service.get_uast_node(node_id)
    return APIResponse.ok(
        UastNodeSchema(
            id=node.uid,
            name=node.name,
            file_id=node.file_node_uid,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            start_point=(node.start_row, node.start_column),
            end_point=(node.end_row, node.end_column),
        )
    )


@router.get(
    "/nodes/{node_id}/content",
    summary="Get node's source code as string",
    response_model=ResponseSuccessSchema[str],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
async def get_node_content(
    node_id: str, graph_service: GraphServiceDep, user: CurrentAgent
):
    res = graph_service.get_node_content(node_id)
    return APIResponse.ok(res)


@router.get(
    "/nodes/{node_id}/usages",
    response_model=ResponseSuccessSchema[list[str]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def check_node_usages(node_id: str, graph_service: GraphServiceDep, user: CurrentAgent):
    res = graph_service.find_usage(node_id)
    return APIResponse.ok(res)


@router.get(
    "/nodes/{node_id}/callees",
    response_model=ResponseSuccessSchema[list[str]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_node_callees(node_id: str, graph_service: GraphServiceDep, user: CurrentAgent):
    res = graph_service.find_callees(node_id)
    return APIResponse.ok(res)
