from .model import (
    ProjectNodeModel,
    FileNodeModel,
    UASTNodeModel,
    TypeDefinitionNodeModel,
    FunctionNodeModel,
)
from typing import cast, Annotated
from app.core.s3 import get_s3_client
from app.core.config import settings
from app.core import AppException, ErrorCode
from mypy_boto3_s3 import S3Client
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)


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
            callees.append({
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


def get_graph_service(
    s3_client: Annotated[S3Client, Depends(get_s3_client)],
) -> GraphService:
    return GraphService(s3_client)


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
