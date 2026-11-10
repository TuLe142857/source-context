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
from app.core.s3 import get_s3_client
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
        return node

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

    def get_file_structure(self, file_id: str) -> list[dict]:
        """
        Args:
            file_id: FileNodeModel's uid

        Returns:
            file structure as list

        Raises:
            AppException:
                ErrorCode.RESOURCE_NOT_FOUND
        """

        file_node = self.get_file_node(file_id)

        def build_result(n: TypeDefinitionNodeModel | FunctionNodeModel) -> dict:
            res = {"id": n.uid, "name": n.name, "type": n.kind, "children": []}
            for c in n.children.all():
                if isinstance(c, TypeDefinitionNodeModel) or isinstance(
                    c, FunctionNodeModel
                ):
                    res["children"].append(build_result(c))
            return res

        nodes: list[UASTNodeModel] = file_node.children.all()
        result = []
        for node in nodes:
            if not (
                isinstance(node, TypeDefinitionNodeModel)
                or isinstance(node, FunctionNodeModel)
            ):
                continue
            result.append(build_result(node))

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
