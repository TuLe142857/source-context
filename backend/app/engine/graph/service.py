from .model import (
    ProjectNodeModel,
    FileNodeModel,
    UASTNodeModel,
    TypeDefinitionNodeModel,
    FunctionNodeModel,
    ApiNodeModel,
    ApiEndpointNodeModel,
    ApiCallNodeModel,
)
from typing import cast, Annotated, Any
from app.infra.s3 import get_s3_client
from app.core.config import settings
from app.core import AppException, ErrorCode
from mypy_boto3_s3 import S3Client
from fastapi import Depends
from neomodel import db
import logging

logger = logging.getLogger(__name__)

_UNUSED_NODES_CONDITION = """
WHERE d.kind IN ["function", "method", "class"]
  AND NOT EXISTS {
    MATCH (d)-[:PARENT_OF*0..]->()<-[:REFERENCE_TO]-(r)
    WHERE NOT (
        r.file_node_uid = d.file_node_uid
        AND r.start_byte >= d.start_byte
        AND r.end_byte <= d.end_byte
    )
  }
RETURN d
ORDER BY d.file_node_uid, d.start_byte
"""
"""Only functions, methods and classes are checked: the call graph does not record plain
reads of a name (``return x``), so variables, parameters and constants would always look
unused. A node is unused when neither it nor any of its children is referenced from
outside its own span - recursion does not count, a used method keeps its class alive."""

_UNUSED_NODES_IN_PROJECT_QUERY = (
    """
MATCH (:Project {uid: $project_id})-[:INCLUDES]->(:File)
      -[:DECLARE]->()-[:PARENT_OF*0..]->(d:Definition)
"""
    + _UNUSED_NODES_CONDITION
)

_UNUSED_NODES_IN_FILE_QUERY = (
    """
MATCH (:File {uid: $file_id})-[:DECLARE]->()-[:PARENT_OF*0..]->(d:Definition)
"""
    + _UNUSED_NODES_CONDITION
)

_API_ENDPOINTS_IN_PROJECT_QUERY = """
MATCH (:Project {uid: $project_id})-[:EXPOSES_API]->(e:ApiEndpoint)
OPTIONAL MATCH (h:Node)-[:HANDLES_API]->(e)
OPTIONAL MATCH (f:File {uid: e.file_node_uid})
OPTIONAL MATCH (c:ApiCall)-[:RESOLVES_TO]->(e)
WITH e, h, f, count(DISTINCT c) AS caller_count
RETURN e, h.uid, h.start_row, f.relative_path, caller_count
"""
"""Endpoints of a project (API nodes written by app/engine/api_map), with their handler
node, file path and the number of calls resolved to them."""

_API_CALLS_IN_PROJECT_QUERY = """
MATCH (:Project {uid: $project_id})-[:HAS_API_CALL]->(c:ApiCall)
OPTIONAL MATCH (n:Node)-[:MAKES_API_CALL]->(c)
OPTIONAL MATCH (f:File {uid: c.file_node_uid})
OPTIONAL MATCH (c)-[r:RESOLVES_TO]->(e:ApiEndpoint)
WITH c, n, f, collect(
    CASE WHEN e IS NULL THEN NULL ELSE {
        endpoint_id: e.uid, project_id: e.project_id, signature: e.signature,
        rule: r.rule, confidence: r.confidence
    } END
) AS targets
RETURN c, n.uid, n.start_row, f.relative_path, targets
"""
"""API calls of a project, with their call node, file path and the endpoints they resolve to."""


class GraphService:
    def __init__(self, s3_client: S3Client):
        self.s3_client = s3_client

    def get_uast_node(self, node_id: str) -> UASTNodeModel:
        """
        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        node = UASTNodeModel.nodes.get_or_none(uid=node_id)
        if node is None:
            raise AppException(ErrorCode.RESOURCE_NOT_FOUND)
        return cast(UASTNodeModel, node)

    def get_project_node(self, project_id: int) -> ProjectNodeModel:
        """
        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        project_node: ProjectNodeModel | None = ProjectNodeModel.nodes.get_or_none(
            uid=project_id
        )
        if project_node is None:
            raise AppException(ErrorCode.RESOURCE_NOT_FOUND)
        return project_node

    def get_file_node(self, file_id: str) -> FileNodeModel:
        """
        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        file_node: FileNodeModel | None = FileNodeModel.nodes.get_or_none(uid=file_id)
        if file_node is None:
            raise AppException(ErrorCode.RESOURCE_NOT_FOUND)
        return file_node

    def list_files_in_projects(self, project_id: int) -> list[tuple[str, str]]:
        """
        Returns:
            list[ tuple[filepath, file_node_id] ]

        Raises:
            AppException:
                With ErrorCode.RESOURCE_NOT_FOUND - project not found

        """
        project_node = self.get_project_node(project_id)
        file_nodes: list[FileNodeModel] = project_node.files.all()
        return [
            (f.relative_path, f.uid) for f in file_nodes if f.relative_path is not None
        ]

    def find_files_by_path(
        self,
        query: str,
        project_ids: list[int] | None = None,
        limit: int = 5,
    ) -> list[FileNodeModel]:
        """Find FileNodeModels matching a path or name query.

        Args:
            query (str): File name, relative path, or partial path query.
            project_ids (list[int] | None, optional): Optional list of project UIDs to filter within. Defaults to None.
            limit (int, optional): Maximum number of files to return. Defaults to 5.

        Returns:
            list[FileNodeModel]: List of matched FileNodeModel instances.
        """
        clean_query = query.strip().lstrip("/")
        if not clean_query:
            return []

        has_project_filter = bool(project_ids)
        params: dict[str, Any] = {
            "query": clean_query,
            "has_project_filter": has_project_filter,
            "project_ids": project_ids or [],
            "limit": limit,
        }

        # Step 1: Exact, Suffix, or Filename match
        cypher = """
        MATCH (p:Project)-[:INCLUDES]->(f:File)
        WHERE ($has_project_filter = false OR p.uid IN $project_ids)
          AND (
            f.uid = $query
            OR f.relative_path = $query
            OR f.name = $query
            OR f.relative_path ENDS WITH ('/' + $query)
            OR $query ENDS WITH ('/' + f.relative_path)
            OR toLower(f.name) = toLower($query)
            OR toLower(f.relative_path) ENDS WITH toLower($query)
          )
        RETURN f
        LIMIT $limit
        """
        rows, _ = db.cypher_query(cypher, params, resolve_objects=True)
        file_nodes: list[FileNodeModel] = [
            row[0] for row in rows if isinstance(row[0], FileNodeModel)
        ]

        # Step 2: Fallback substring match if no exact/suffix match found
        if not file_nodes:
            fallback_cypher = """
            MATCH (p:Project)-[:INCLUDES]->(f:File)
            WHERE ($has_project_filter = false OR p.uid IN $project_ids)
              AND (
                toLower(f.name) CONTAINS toLower($query)
                OR toLower(f.relative_path) CONTAINS toLower($query)
              )
            RETURN f
            LIMIT $limit
            """
            fb_rows, _ = db.cypher_query(fallback_cypher, params, resolve_objects=True)
            file_nodes = [
                row[0] for row in fb_rows if isinstance(row[0], FileNodeModel)
            ]

        return file_nodes

    def get_file_structure(self, file_id: str) -> list[dict[str, Any]]:
        """Retrieves hierarchical file structure including classes, methods, and functions.

        Args:
            file_id (str): FileNodeModel's uid.

        Returns:
            list[dict[str, Any]]: Hierarchical list of definitions with signatures,
                line ranges, docstrings, and summaries.

        Raises:
            AppException: ErrorCode.RESOURCE_NOT_FOUND if file is not found.
        """
        file_node = self.get_file_node(file_id)

        def _build_node_dict(
            n: TypeDefinitionNodeModel | FunctionNodeModel,
        ) -> dict[str, Any]:
            children_res: list[dict[str, Any]] = []
            for c in n.children.all():
                if isinstance(c, (TypeDefinitionNodeModel, FunctionNodeModel)):
                    children_res.append(_build_node_dict(c))

            return {
                "id": n.uid,
                "name": n.name,
                "type": getattr(n, "kind", n.node_type),
                "signature": getattr(n, "signature", None),
                "summary": getattr(n, "summary", None),
                "docstring": n.docstring,
                "start_row": n.start_row,
                "end_row": n.end_row,
                "start_column": n.start_column,
                "end_column": n.end_column,
                "children": children_res,
            }

        nodes: list[UASTNodeModel] = file_node.children.all()
        result: list[dict[str, Any]] = []
        for node in nodes:
            if isinstance(node, (TypeDefinitionNodeModel, FunctionNodeModel)):
                result.append(_build_node_dict(node))

        return result

    def get_file_content(self, file_node_id: str) -> bytes | None:
        """
        Returns:
            None if file_source_code key is not stored on file node.
        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND

        """
        file_node = self.get_file_node(file_node_id)

        if (file_node.source_code_key is None) or (len(file_node.source_code_key) == 0):
            return None

        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=settings.S3_DEFAULT_BUCKET, Key=file_node.source_code_key
        )
        return response["Body"].read()

    def get_node_content(self, node_uid: str) -> str | None:
        """
        Get the source code of an `UASTNodeModel`
        Args:
            node_uid: uid of the `UASTNodeModel`
        Returns:
        """
        node = self.get_uast_node(node_uid)

        source_bytes = self.get_file_content(node.file_node_uid)
        if source_bytes is None:
            return None
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8")

    def find_usage(self, node_id: str) -> list[dict] | None:
        """
        Find nodes that reference to this node
        Args:
            node_id: this node's uid

        Returns:
            - ``list[node_id]`` of nodes that reference to this node.
            - ``None`` if node_uid is not found.
        """
        node = self.get_uast_node(node_id)
        refs_by: list[UASTNodeModel] = node.referenced_by.all()
        return [
            {
                "id": r.uid,
                "name": r.name,
                "file_id": r.file_node_uid,
                "node_type": r.node_type,
                "kind": getattr(r, "kind", None),
            }
            for r in refs_by
        ]

    def find_callees(self, node_uid: str) -> list[dict] | None:
        """
        Find nodes that this node or its children reference to.

        Args:
            node_uid:
        Returns:
            - ``list[node_id]`` of nodes that this node or its children reference to
            - ``None`` if node_uid is not found.
        """

        node = self.get_uast_node(node_uid)

        callees: list[dict] = []

        for r in cast(list[UASTNodeModel], node.references.all()):
            callees.append(
                {
                    "id": r.uid,
                    "name": r.name,
                    "file_id": r.file_node_uid,
                    "node_type": r.node_type,
                    "kind": getattr(r, "kind", None),
                }
            )

        for child in cast(list[UASTNodeModel], node.children.all()):
            child_callees = self.find_callees(child.uid)
            if child_callees is not None:
                callees += child_callees

        return callees

    def find_symbol_definitions(
        self,
        symbol: str,
        file_query: str | None = None,
        project_ids: list[int] | None = None,
        limit: int = 5,
    ) -> list[tuple[UASTNodeModel, FileNodeModel]]:
        """Find definition nodes and their parent files matching a symbol name.

        Args:
            symbol (str): Symbol name (function, class, method).
            file_query (str | None, optional): Optional file name or path filter. Defaults to None.
            project_ids (list[int] | None, optional): Optional project IDs filter. Defaults to None.
            limit (int, optional): Maximum definitions to return. Defaults to 5.

        Returns:
            list[tuple[UASTNodeModel, FileNodeModel]]: List of (definition_node, file_node) tuples.
        """
        clean_symbol = symbol.strip()
        if not clean_symbol:
            return []

        has_project_filter = bool(project_ids)
        clean_file = file_query.strip().lstrip("/") if file_query else ""
        has_file_filter = bool(clean_file)

        params: dict[str, Any] = {
            "symbol": clean_symbol,
            "has_project_filter": has_project_filter,
            "project_ids": project_ids or [],
            "has_file_filter": has_file_filter,
            "file_query": clean_file,
            "limit": limit,
        }

        cypher = """
        MATCH (p:Project)-[:INCLUDES]->(f:File)-[:DECLARE]->()-[:PARENT_OF*0..]->(d:Definition)
        WHERE ($has_project_filter = false OR p.uid IN $project_ids)
          AND ($has_file_filter = false OR f.relative_path = $file_query OR f.relative_path ENDS WITH ('/' + $file_query) OR f.name = $file_query)
          AND (d.name = $symbol OR toLower(d.name) = toLower($symbol))
        RETURN d, f
        LIMIT $limit
        """
        rows, _ = db.cypher_query(cypher, params, resolve_objects=True)
        results: list[tuple[UASTNodeModel, FileNodeModel]] = []
        for row in rows:
            if (
                len(row) >= 2
                and isinstance(row[0], UASTNodeModel)
                and isinstance(row[1], FileNodeModel)
            ):
                results.append((row[0], row[1]))

        return results

    def get_rich_usages(self, node_uid: str) -> list[dict[str, Any]]:
        """Find rich details of all nodes that call or reference this node or its members.

        Args:
            node_uid (str): The target node's UID.

        Returns:
            list[dict[str, Any]]: List of rich caller usage dictionaries.
        """
        cypher = """
        MATCH (target:Node {uid: $node_uid})
        MATCH (target)-[:PARENT_OF*0..]->(member:Node)<-[:REFERENCE_TO]-(ref:Node)
        OPTIONAL MATCH (enclosing:Definition)-[:PARENT_OF*0..]->(ref)
        OPTIONAL MATCH (f:File {uid: ref.file_node_uid})
        WHERE NOT (
            ref.file_node_uid = target.file_node_uid
            AND ref.start_byte >= target.start_byte
            AND ref.end_byte <= target.end_byte
        )
        RETURN 
            ref.uid AS ref_id,
            ref.name AS ref_name,
            ref.node_type AS ref_type,
            ref.start_row AS ref_start_row,
            ref.end_row AS ref_end_row,
            f.relative_path AS file_path,
            f.uid AS file_id,
            enclosing.uid AS enclosing_id,
            enclosing.name AS enclosing_name,
            enclosing.kind AS enclosing_kind,
            enclosing.signature AS enclosing_signature,
            enclosing.start_row AS enclosing_start_row,
            enclosing.end_row AS enclosing_end_row,
            enclosing.docstring AS enclosing_docstring,
            enclosing.summary AS enclosing_summary
        """
        rows, cols = db.cypher_query(cypher, {"node_uid": node_uid})
        seen: dict[str, dict[str, Any]] = {}
        for row in rows:
            record = dict(zip(cols, row))
            enclosing_id = record.get("enclosing_id")
            key = enclosing_id or record.get("ref_id")
            if not key:
                continue

            ref_start = record.get("ref_start_row")
            if key not in seen:
                seen[key] = {
                    "caller_id": enclosing_id or record.get("ref_id"),
                    "caller_name": record.get("enclosing_name")
                    or record.get("ref_name"),
                    "caller_kind": record.get("enclosing_kind")
                    or record.get("ref_type"),
                    "caller_signature": record.get("enclosing_signature"),
                    "file_path": record.get("file_path"),
                    "file_id": record.get("file_id"),
                    "start_row": record.get("enclosing_start_row")
                    or record.get("ref_start_row"),
                    "end_row": record.get("enclosing_end_row")
                    or record.get("ref_end_row"),
                    "call_lines": [ref_start] if ref_start is not None else [],
                    "docstring": record.get("enclosing_docstring"),
                    "summary": record.get("enclosing_summary"),
                }
            else:
                if ref_start is not None and ref_start not in seen[key]["call_lines"]:
                    seen[key]["call_lines"].append(ref_start)

        return list(seen.values())

    def get_rich_callees(self, node_uid: str) -> list[dict[str, Any]]:
        """Find rich details of all nodes that this node or its children call or reference.

        Args:
            node_uid (str): The target node's UID.

        Returns:
            list[dict[str, Any]]: List of rich callee dictionaries.
        """
        cypher = """
        MATCH (target:Node {uid: $node_uid})
        MATCH (target)-[:PARENT_OF*0..]->(ref:Node)-[:REFERENCE_TO]->(callee:Node)
        OPTIONAL MATCH (f:File {uid: callee.file_node_uid})
        RETURN DISTINCT
            callee.uid AS callee_id,
            callee.name AS callee_name,
            callee.node_type AS callee_type,
            callee.signature AS callee_signature,
            callee.start_row AS callee_start_row,
            callee.end_row AS callee_end_row,
            callee.docstring AS callee_docstring,
            callee.summary AS callee_summary,
            f.relative_path AS file_path,
            f.uid AS file_id,
            ref.start_row AS call_line
        """
        rows, cols = db.cypher_query(cypher, {"node_uid": node_uid})
        callees_map: dict[str, dict[str, Any]] = {}
        for row in rows:
            record = dict(zip(cols, row))
            c_id = record.get("callee_id")
            if not c_id or c_id == node_uid:
                continue
            call_line = record.get("call_line")
            if c_id not in callees_map:
                callees_map[c_id] = {
                    "callee_id": c_id,
                    "callee_name": record.get("callee_name"),
                    "callee_kind": getattr(
                        record.get("callee_type"), "value", record.get("callee_type")
                    ),
                    "callee_signature": record.get("callee_signature"),
                    "file_path": record.get("file_path"),
                    "file_id": record.get("file_id"),
                    "start_row": record.get("callee_start_row"),
                    "end_row": record.get("callee_end_row"),
                    "docstring": record.get("callee_docstring"),
                    "summary": record.get("callee_summary"),
                    "call_lines": [call_line] if call_line is not None else [],
                }
            else:
                if (
                    call_line is not None
                    and call_line not in callees_map[c_id]["call_lines"]
                ):
                    callees_map[c_id]["call_lines"].append(call_line)

        return list(callees_map.values())

    def get_unused_nodes_in_project(self, project_id: int) -> list[dict]:
        """
        Find functions, methods and classes in project that are not referenced anywhere.
        Only functions, methods and classes are checked.

        Args:
            project_id: ProjectNodeModel's uid

        Returns:
            ``list[dict]`` of unused nodes

        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        self.get_project_node(project_id)
        return self._find_unused_nodes(
            _UNUSED_NODES_IN_PROJECT_QUERY, {"project_id": project_id}
        )

    def get_unused_nodes_in_file(self, file_id: str) -> list[dict]:
        """
        Find functions, methods and classes in file that are not referenced anywhere.
        Only functions, methods and classes are checked.

        Args:
            file_id: FileNodeModel's uid

        Returns:
            ``list[dict]`` of unused nodes

        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        self.get_file_node(file_id)
        return self._find_unused_nodes(
            _UNUSED_NODES_IN_FILE_QUERY, {"file_id": file_id}
        )

    def _find_unused_nodes(self, query: str, params: dict) -> list[dict]:
        rows, _ = db.cypher_query(query, params, resolve_objects=True)
        nodes: list[UASTNodeModel] = [row[0] for row in rows]
        return [
            {
                "id": n.uid,
                "name": n.name,
                "file_id": n.file_node_uid,
                "node_type": n.node_type,
                "kind": getattr(n, "kind", None),
            }
            for n in nodes
        ]

    def list_api_endpoints_in_project(self, project_id: int) -> list[dict[str, Any]]:
        """
        List the API endpoints a project serves, sorted by protocol and signature.

        Args:
            project_id: ProjectNodeModel's uid

        Returns:
            ``list[dict]`` of endpoints; ``details`` holds the protocol-specific fields

        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        self.get_project_node(project_id)
        rows, _ = db.cypher_query(
            _API_ENDPOINTS_IN_PROJECT_QUERY,
            {"project_id": project_id},
            resolve_objects=True,
        )
        result = []
        for endpoint, handler_uid, handler_row, file_path, caller_count in rows:
            metadata = endpoint.metadata or {}
            result.append(
                {
                    "id": endpoint.uid,
                    "protocol": endpoint.protocol,
                    "signature": endpoint.signature,
                    "framework": endpoint.framework,
                    "file_id": endpoint.file_node_uid,
                    "file_path": file_path,
                    "handler_node_id": handler_uid,
                    "handler_name": metadata.get("handler"),
                    "start_line": _line(handler_row),
                    "caller_count": caller_count,
                    "details": _api_details(endpoint, ApiEndpointNodeModel),
                    "metadata": metadata,
                }
            )
        return sorted(result, key=lambda e: (e["protocol"], e["signature"] or ""))

    def list_api_calls_in_project(self, project_id: int) -> list[dict[str, Any]]:
        """
        List the API calls a project makes, in source order, with the endpoints they
        resolve to.

        Args:
            project_id: ProjectNodeModel's uid

        Returns:
            ``list[dict]`` of calls; ``details`` holds the protocol-specific fields

        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """
        self.get_project_node(project_id)
        rows, _ = db.cypher_query(
            _API_CALLS_IN_PROJECT_QUERY,
            {"project_id": project_id},
            resolve_objects=True,
        )
        result = []
        for call, call_uid, call_row, file_path, targets in rows:
            metadata = call.metadata or {}
            result.append(
                {
                    "id": call.uid,
                    "protocol": call.protocol,
                    "signature": call.signature,
                    "library": call.library,
                    "target_hint": call.target_hint,
                    "is_dynamic": bool(call.is_dynamic),
                    "file_id": call.file_node_uid,
                    "file_path": file_path,
                    "call_node_id": call_uid,
                    "scope": metadata.get("scope"),
                    "start_line": _line(call_row),
                    "targets": sorted(targets, key=lambda t: -(t["confidence"] or 0)),
                    "details": _api_details(call, ApiCallNodeModel),
                    "metadata": metadata,
                }
            )
        return sorted(
            result, key=lambda c: (c["file_path"] or "", c["start_line"] or 0, c["id"])
        )


def _api_details(node: ApiNodeModel, role: type[ApiNodeModel]) -> dict[str, Any]:
    """Protocol-specific properties: those the concrete class adds to its role class
    (``RestEndpointNodeModel`` -> ``http_method``, ``path``, ``path_params``), so a new
    protocol model shows up here without touching the API."""

    common = role.defined_properties(rels=False)
    return {
        name: getattr(node, name)
        for name in type(node).defined_properties(rels=False)
        if name not in common
    }


def _line(row: int | None) -> int | None:
    """0-based UAST row -> 1-based line."""

    return row + 1 if row is not None else None


def get_graph_service(
    s3_client: Annotated[S3Client, Depends(get_s3_client)],
) -> GraphService:
    return GraphService(s3_client)


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
