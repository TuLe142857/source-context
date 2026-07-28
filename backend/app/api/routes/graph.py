from fastapi import APIRouter, Path
from fastapi.concurrency import run_in_threadpool
from app.graph.query import GraphQuery
from app.graph.model import UASTNodeModel

router = APIRouter(prefix="/graph", tags=["Graph Query"])


async def check_project_access(user_id: int, project_id: int) -> bool:
    return True


async def check_file_access(user_id: int, file_id: str) -> bool:
    return True


async def check_node_access(user_id: int, node_id: str) -> bool:
    return True


@router.get("/projects/{project_id}/files", summary="Get files in project")
async def get_files(
    project_id: int,
):
    results: list[tuple[str, str]] | None = await run_in_threadpool(
        GraphQuery.list_files_in_projects, project_id
    )
    return results


@router.get("/files/{file_id}/structures")
async def get_file_structures(
    file_id: str,
):
    res = await run_in_threadpool(GraphQuery.get_file_structure, file_id)
    return res


@router.get("/files/{file_id}/contents", summary="Get contents of file")
async def get_file_contents(
    file_id: str,
):
    result = await run_in_threadpool(GraphQuery.get_file_content, file_id)
    return result


@router.get("/nodes/{node_id}")
async def get_node_info(node_id: str):
    node: UASTNodeModel = await run_in_threadpool(GraphQuery.get_node, node_id)
    return {"id": node.uid, "name": node.name, "file_id": node.file_node_uid}


@router.get("/nodes/{node_id}/content", summary="Get node's source code as string")
async def get_node_content(
    node_id: str,
):
    results = await run_in_threadpool(GraphQuery.get_node_content, node_id)
    return results


@router.get("/nodes/{node_id}/usage")
async def check_node_usages(
    node_id: str,
):
    results: list[str] = await run_in_threadpool(GraphQuery.find_usage, node_id)
    return results


@router.get("/nodes/{node_id}/calleees}")
async def get_node_callees(
    node_id: str,
):
    results = await run_in_threadpool(GraphQuery.find_callees, node_id)
    return results
