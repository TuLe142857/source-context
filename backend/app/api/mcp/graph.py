import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies import CodeRetrieverDep, CurrentAgent, DBSession
from app.core import (
    APIResponse,
    AppException,
    ErrorCode,
    ResponseSuccessSchema,
    build_error_docs,
)
from app.graph.model import FileNodeModel, UASTNodeModel
from app.graph.service import GraphService, GraphServiceDep
from app.model.branch import Branch
from app.model.project import Project
from app.retrieval.retriever import CodeRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["Graph Query"])


class FileInfo(BaseModel):
    id: str
    path: str


class FileStructureNode(BaseModel):
    id: str
    name: str | None = None
    type: str | None = None
    signature: str | None = None
    summary: str | None = None
    docstring: str | None = None
    start_row: int | None = None
    end_row: int | None = None
    start_column: int | None = None
    end_column: int | None = None
    children: list["FileStructureNode"] = []


class FileStructureResult(BaseModel):
    file_id: str
    file_path: str
    matched_by: str = "path_match"
    matched_symbol: str | None = None
    structure: list[FileStructureNode] = []


class NodeUsageItem(BaseModel):
    caller_id: str
    caller_name: str | None = None
    caller_kind: str | None = None
    caller_signature: str | None = None
    file_path: str | None = None
    file_id: str | None = None
    start_row: int | None = None
    end_row: int | None = None
    call_lines: list[int] = []
    docstring: str | None = None
    summary: str | None = None


class NodeCalleeItem(BaseModel):
    callee_id: str
    callee_name: str | None = None
    callee_kind: str | None = None
    callee_signature: str | None = None
    file_path: str | None = None
    file_id: str | None = None
    start_row: int | None = None
    end_row: int | None = None
    call_lines: list[int] = []
    docstring: str | None = None
    summary: str | None = None


class TargetSymbolInfo(BaseModel):
    id: str
    name: str | None = None
    kind: str | None = None
    signature: str | None = None
    file_path: str | None = None
    file_id: str | None = None
    start_row: int | None = None
    end_row: int | None = None
    docstring: str | None = None
    summary: str | None = None


class ImpactAnalysisResponse(BaseModel):
    target: TargetSymbolInfo
    usages: list[NodeUsageItem] = []
    callees: list[NodeCalleeItem] = []
    files_affected: list[str] = []
    total_usages: int = 0


async def _resolve_project_ids(
    db: DBSession,
    project_id: int | None,
    repository_id: int | None,
    workspace_id: int | None,
) -> list[int] | None:
    if project_id is not None:
        return [project_id]
    if repository_id is not None:
        stmt = (
            select(Project.id)
            .join(Branch, Project.branch_id == Branch.id)
            .where(Branch.repository_id == repository_id)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())
    if workspace_id is not None:
        stmt = select(Project.id).where(Project.workspace_id == workspace_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())
    return None


async def _resolve_target_symbol(
    symbol: str | None,
    node_id: str | None,
    file: str | None,
    project_ids: list[int] | None,
    workspace_id: int | None,
    graph_service: GraphService,
    code_retriever: CodeRetriever,
) -> tuple[UASTNodeModel, FileNodeModel | None]:
    if node_id:
        target_node = graph_service.get_uast_node(node_id)
        file_node = None
        if target_node.file_node_uid:
            try:
                file_node = graph_service.get_file_node(target_node.file_node_uid)
            except AppException:
                pass
        return target_node, file_node

    if not symbol:
        raise AppException(
            ErrorCode.RESOURCE_NOT_FOUND,
            message="Either 'symbol' or 'node_id' must be provided.",
        )

    # 1. Search Neo4j definitions
    defs = graph_service.find_symbol_definitions(
        symbol=symbol,
        file_query=file,
        project_ids=project_ids,
        limit=5,
    )
    if defs:
        return defs[0][0], defs[0][1]

    # 2. Fallback to vector search
    try:
        hits = code_retriever.retrieve(
            query=symbol,
            top_k=3,
            workspace_id=workspace_id,
        )
    except (ConnectionError, RuntimeError, ValueError) as exc:
        logger.warning(
            "Vector retrieval fallback failed for symbol '%s': %s", symbol, exc
        )
        hits = []

    for hit in hits:
        if not hit.node_id:
            continue
        try:
            target_node = graph_service.get_uast_node(hit.node_id)
            file_node = None
            if target_node.file_node_uid:
                try:
                    file_node = graph_service.get_file_node(target_node.file_node_uid)
                except AppException:
                    pass
            return target_node, file_node
        except AppException:
            continue

    raise AppException(
        ErrorCode.RESOURCE_NOT_FOUND,
        message=f"Symbol '{symbol}' could not be resolved.",
    )


class NodeInfo(BaseModel):
    id: str
    name: str | None
    file_id: str | None


class UastNodeSchema(BaseModel):
    id: str
    name: str | None = None
    file_id: str
    start_byte: int
    end_byte: int
    start_point: tuple[int, int]
    end_point: tuple[int, int]
    signature: str | None = None
    summary: str | None = None
    docstring: str | None = None


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
) -> APIResponse:
    res = [
        FileInfo(path=_[0], id=_[1])
        for _ in graph_service.list_files_in_projects(project_id)
    ]
    return APIResponse.ok(res)


@router.get(
    "/projects/{project_id}/unused-nodes",
    summary="Find unused functions, methods and classes in project",
    response_model=ResponseSuccessSchema[list[dict]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_unused_nodes_in_project(
    project_id: int,
    graph_service: GraphServiceDep,
    user: CurrentAgent,
) -> APIResponse:
    res = graph_service.get_unused_nodes_in_project(project_id)
    return APIResponse.ok(res)


@router.get(
    "/files/structure",
    summary="Resolve and get rich structure of files by name, path, function name, or ID",
    response_model=ResponseSuccessSchema[list[FileStructureResult]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
async def resolve_file_structure(
    graph_service: GraphServiceDep,
    code_retriever: CodeRetrieverDep,
    db: DBSession,
    user: CurrentAgent,
    file: str | None = None,
    file_id: str | None = None,
    repository_id: int | None = None,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> APIResponse:
    query = file or file_id
    if not query:
        raise AppException(
            ErrorCode.RESOURCE_NOT_FOUND,
            message="Either 'file' or 'file_id' query parameter must be provided.",
        )

    # 1. Resolve project_ids from repository_id or workspace_id
    project_ids = await _resolve_project_ids(
        db, project_id, repository_id, workspace_id
    )

    matched_results: list[FileStructureResult] = []

    # 2. Case 1 & Case 3: Try path/name/ID matching in Neo4j
    file_nodes = graph_service.find_files_by_path(
        query=query, project_ids=project_ids, limit=3
    )

    if file_nodes:
        for f_node in file_nodes:
            structure = [
                FileStructureNode(**node_data)
                for node_data in graph_service.get_file_structure(f_node.uid)
            ]
            matched_results.append(
                FileStructureResult(
                    file_id=f_node.uid,
                    file_path=f_node.relative_path or f_node.name,
                    matched_by="path_match",
                    matched_symbol=None,
                    structure=structure,
                )
            )
        return APIResponse.ok(matched_results)

    # 3. Case 2: No file matched by path -> Fallback to semantic vector search
    try:
        hits = code_retriever.retrieve(
            query=query,
            top_k=3,
            workspace_id=workspace_id,
        )
    except (ConnectionError, RuntimeError, ValueError) as exc:
        logger.warning("Vector retrieval fallback failed for '%s': %s", query, exc)
        hits = []

    seen_file_ids: set[str] = set()
    for hit in hits:
        if not hit.node_id:
            continue
        try:
            uast_node = graph_service.get_uast_node(hit.node_id)
        except AppException:
            continue

        if uast_node.file_node_uid and uast_node.file_node_uid not in seen_file_ids:
            seen_file_ids.add(uast_node.file_node_uid)
            try:
                f_node = graph_service.get_file_node(uast_node.file_node_uid)
            except AppException:
                continue

            # Check project filter if active
            if project_ids:
                proj = f_node.project.single()
                if proj and proj.uid not in project_ids:
                    continue

            structure = [
                FileStructureNode(**node_data)
                for node_data in graph_service.get_file_structure(f_node.uid)
            ]
            matched_results.append(
                FileStructureResult(
                    file_id=f_node.uid,
                    file_path=f_node.relative_path or f_node.name,
                    matched_by="semantic_search",
                    matched_symbol=hit.name,
                    structure=structure,
                )
            )
            if len(matched_results) >= 2:
                break

    return APIResponse.ok(matched_results)


@router.get(
    "/files/{file_id}/structure",
    response_model=ResponseSuccessSchema[list[FileStructureNode]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_file_structure(
    file_id: str,
    graph_service: GraphServiceDep,
    user: CurrentAgent,
) -> APIResponse:
    res = graph_service.get_file_structure(file_id)
    return APIResponse.ok(res)


@router.get(
    "/files/content",
    summary="Get contents of file by path, name, or ID",
    response_model=ResponseSuccessSchema[str | None],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
async def resolve_file_content(
    graph_service: GraphServiceDep,
    db: DBSession,
    user: CurrentAgent,
    file: str | None = None,
    file_id: str | None = None,
    repository_id: int | None = None,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> APIResponse:
    query = file or file_id
    if not query:
        raise AppException(
            ErrorCode.RESOURCE_NOT_FOUND,
            message="Either 'file' or 'file_id' must be provided.",
        )

    project_ids = await _resolve_project_ids(
        db, project_id, repository_id, workspace_id
    )
    file_nodes = graph_service.find_files_by_path(
        query=query, project_ids=project_ids, limit=1
    )
    if not file_nodes:
        raise AppException(
            ErrorCode.RESOURCE_NOT_FOUND,
            message=f"File '{query}' not found.",
        )

    content_bytes = graph_service.get_file_content(file_nodes[0].uid)
    content_str = (
        content_bytes.decode("utf-8", errors="replace")
        if content_bytes is not None
        else None
    )
    return APIResponse.ok(content_str)


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
) -> APIResponse:
    res = graph_service.get_file_content(file_id)
    return APIResponse.ok(res)


@router.get(
    "/files/{file_id}/unused-nodes",
    summary="Find unused functions, methods and classes in file",
    response_model=ResponseSuccessSchema[list[dict]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_unused_nodes_in_file(
    file_id: str,
    graph_service: GraphServiceDep,
    user: CurrentAgent,
) -> APIResponse:
    res = graph_service.get_unused_nodes_in_file(file_id)
    return APIResponse.ok(res)


@router.get(
    "/nodes/impact",
    summary="Analyze the impact of modifying a symbol (callers, callees, and affected files)",
    response_model=ResponseSuccessSchema[ImpactAnalysisResponse],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
async def analyze_symbol_impact(
    graph_service: GraphServiceDep,
    code_retriever: CodeRetrieverDep,
    db: DBSession,
    user: CurrentAgent,
    symbol: str | None = None,
    node_id: str | None = None,
    file: str | None = None,
    repository_id: int | None = None,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> APIResponse:
    """Analyze the impact of modifying a symbol (callers, callees, and affected files).

    Args:
        graph_service (GraphServiceDep): Graph service dependency.
        code_retriever (CodeRetrieverDep): Code retriever dependency.
        db (DBSession): Database session.
        user (CurrentAgent): Current authenticated agent.
        symbol (str | None, optional): Symbol name. Defaults to None.
        node_id (str | None, optional): Node ID. Defaults to None.
        file (str | None, optional): File path or name. Defaults to None.
        repository_id (int | None, optional): Repository ID filter. Defaults to None.
        workspace_id (int | None, optional): Workspace ID filter. Defaults to None.
        project_id (int | None, optional): Project ID filter. Defaults to None.

    Returns:
        APIResponse: Impact analysis response with target, usages, callees, and affected files.
    """
    project_ids = await _resolve_project_ids(
        db, project_id, repository_id, workspace_id
    )
    target_node, file_node = await _resolve_target_symbol(
        symbol=symbol,
        node_id=node_id,
        file=file,
        project_ids=project_ids,
        workspace_id=workspace_id,
        graph_service=graph_service,
        code_retriever=code_retriever,
    )

    target_info = TargetSymbolInfo(
        id=target_node.uid,
        name=target_node.name,
        kind=getattr(target_node, "kind", target_node.node_type),
        signature=getattr(target_node, "signature", None),
        file_path=file_node.relative_path if file_node else None,
        file_id=file_node.uid if file_node else target_node.file_node_uid,
        start_row=target_node.start_row,
        end_row=target_node.end_row,
        docstring=target_node.docstring,
        summary=getattr(target_node, "summary", None),
    )

    raw_usages = graph_service.get_rich_usages(target_node.uid)
    usage_items = [NodeUsageItem(**u) for u in raw_usages]

    raw_callees = graph_service.get_rich_callees(target_node.uid)
    callee_items = [NodeCalleeItem(**c) for c in raw_callees]

    files_affected = sorted(list({u.file_path for u in usage_items if u.file_path}))

    return APIResponse.ok(
        ImpactAnalysisResponse(
            target=target_info,
            usages=usage_items,
            callees=callee_items,
            files_affected=files_affected,
            total_usages=len(usage_items),
        )
    )


@router.get(
    "/nodes/usages",
    summary="Find rich caller usages of a symbol or node",
    response_model=ResponseSuccessSchema[list[NodeUsageItem]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
async def find_symbol_usages(
    graph_service: GraphServiceDep,
    code_retriever: CodeRetrieverDep,
    db: DBSession,
    user: CurrentAgent,
    symbol: str | None = None,
    node_id: str | None = None,
    file: str | None = None,
    repository_id: int | None = None,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> APIResponse:
    """Find rich caller usages of a symbol or node across projects.

    Args:
        graph_service (GraphServiceDep): Graph service dependency.
        code_retriever (CodeRetrieverDep): Code retriever dependency.
        db (DBSession): Database session.
        user (CurrentAgent): Current authenticated agent.
        symbol (str | None, optional): Symbol name. Defaults to None.
        node_id (str | None, optional): Direct node UID. Defaults to None.
        file (str | None, optional): File path or name filter. Defaults to None.
        repository_id (int | None, optional): Repository ID filter. Defaults to None.
        workspace_id (int | None, optional): Workspace ID filter. Defaults to None.
        project_id (int | None, optional): Project ID filter. Defaults to None.

    Returns:
        APIResponse: List of rich caller usage items.
    """
    project_ids = await _resolve_project_ids(
        db, project_id, repository_id, workspace_id
    )
    target_node, _ = await _resolve_target_symbol(
        symbol=symbol,
        node_id=node_id,
        file=file,
        project_ids=project_ids,
        workspace_id=workspace_id,
        graph_service=graph_service,
        code_retriever=code_retriever,
    )

    raw_usages = graph_service.get_rich_usages(target_node.uid)
    usage_items = [NodeUsageItem(**u) for u in raw_usages]
    return APIResponse.ok(usage_items)


@router.get(
    "/nodes/callees",
    summary="Find rich callees/dependencies of a symbol or node",
    response_model=ResponseSuccessSchema[list[NodeCalleeItem]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
async def find_symbol_callees(
    graph_service: GraphServiceDep,
    code_retriever: CodeRetrieverDep,
    db: DBSession,
    user: CurrentAgent,
    symbol: str | None = None,
    node_id: str | None = None,
    file: str | None = None,
    repository_id: int | None = None,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> APIResponse:
    """Find rich callees/dependencies of a symbol or node.

    Args:
        graph_service (GraphServiceDep): Graph service dependency.
        code_retriever (CodeRetrieverDep): Code retriever dependency.
        db (DBSession): Database session.
        user (CurrentAgent): Current authenticated agent.
        symbol (str | None, optional): Symbol name. Defaults to None.
        node_id (str | None, optional): Direct node UID. Defaults to None.
        file (str | None, optional): File path or name filter. Defaults to None.
        repository_id (int | None, optional): Repository ID filter. Defaults to None.
        workspace_id (int | None, optional): Workspace ID filter. Defaults to None.
        project_id (int | None, optional): Project ID filter. Defaults to None.

    Returns:
        APIResponse: List of rich callee items.
    """
    project_ids = await _resolve_project_ids(
        db, project_id, repository_id, workspace_id
    )
    target_node, _ = await _resolve_target_symbol(
        symbol=symbol,
        node_id=node_id,
        file=file,
        project_ids=project_ids,
        workspace_id=workspace_id,
        graph_service=graph_service,
        code_retriever=code_retriever,
    )

    raw_callees = graph_service.get_rich_callees(target_node.uid)
    callee_items = [NodeCalleeItem(**c) for c in raw_callees]
    return APIResponse.ok(callee_items)


@router.get(
    "/nodes/{node_id}",
    response_model=ResponseSuccessSchema[UastNodeSchema],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_node_info(
    node_id: str, graph_service: GraphServiceDep, user: CurrentAgent
) -> APIResponse:
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
            signature=getattr(node, "signature", None),
            summary=getattr(node, "summary", None),
            docstring=node.docstring,
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
) -> APIResponse:
    res = graph_service.get_node_content(node_id)
    return APIResponse.ok(res)


@router.get(
    "/nodes/{node_id}/usages",
    response_model=ResponseSuccessSchema[list[str]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def check_node_usages(
    node_id: str, graph_service: GraphServiceDep, user: CurrentAgent
) -> APIResponse:
    res = graph_service.find_usage(node_id)
    return APIResponse.ok(res)


@router.get(
    "/nodes/{node_id}/callees",
    response_model=ResponseSuccessSchema[list[str]],
    responses=build_error_docs(ErrorCode.RESOURCE_NOT_FOUND),
)
def get_node_callees(
    node_id: str, graph_service: GraphServiceDep, user: CurrentAgent
) -> APIResponse:
    res = graph_service.find_callees(node_id)
    return APIResponse.ok(res)
