from .model import (
    ProjectNodeModel,
    FileNodeModel,
    UASTNodeModel,
    TypeDefinitionNodeModel,
    FunctionNodeModel,
)
from typing import cast
from app.core.s3 import get_s3_client
from app.core.config import settings

import logging

logger = logging.getLogger(__name__)


class GraphQuery:
    @staticmethod
    def list_files_in_projects(project_id: int) -> list[tuple[str, str]] | None:
        """
        Note: file path is relative from project root
        Args:
            project_id: project's id.

        Returns:
            list[ tuple(filepath, file_node_id) ]
        """
        project_node: ProjectNodeModel | None = ProjectNodeModel.nodes.get_or_none(
            uid=project_id
        )

        if project_node is None:
            return None

        file_nodes: list[FileNodeModel] = project_node.files.all()
        return [
            (f.relative_path, f.uid) for f in file_nodes if f.relative_path is not None
        ]

    @staticmethod
    def get_file_structure(file_id) -> list | None:
        """
        Args:
            file_id: FileNodeModel's uid

        Returns:
            file structure as list
        """

        file_node: FileNodeModel | None = FileNodeModel.nodes.get_or_none(uid=file_id)
        if file_node is None:
            return None

        def build_result(n: TypeDefinitionNodeModel | FunctionNodeModel) -> dict:
            res = {"id": n.uid, "name": n.name, "type": n.kind, "children": []}
            for c in n.children.all():
                if not (
                    isinstance(c, TypeDefinitionNodeModel)
                    or isinstance(c, FunctionNodeModel)
                ):
                    res["children"].append(build_result(c))
            return res

        nodes: list[UASTNodeModel] = file_node.nodes.all()
        result = []
        for node in nodes:
            if not (
                isinstance(node, TypeDefinitionNodeModel)
                or isinstance(node, FunctionNodeModel)
            ):
                continue
            result.append(build_result(node))

        return result

    @staticmethod
    def get_source_code_of_file(file_node_uid: str) -> bytes | None:
        """
        Get the source code of an `FileNodeModel`
        Args:
            file_node_uid:

        Returns:
            The whole file source code as bytes.
            If FileNodeModel is not found, return None.
        """
        file_node: FileNodeModel | None = FileNodeModel.nodes.get_or_none(
            uid=file_node_uid
        )

        if file_node is None:
            logger.warning(f"File node with uid '{file_node_uid}' not found")
            return None

        if (file_node.source_code_key is None) or (len(file_node.source_code_key) == 0):
            return None

        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=settings.S3_DEFAULT_BUCKET, Key=file_node.source_code_key
        )
        return response["Body"].read()

    @staticmethod
    def get_source_code_of_node(node_uid: str) -> str | None:
        """
        Get the source code of an `UASTNodeModel`
        Args:
            node_uid: uid of the `UASTNodeModel`
        Returns:
        """
        node: UASTNodeModel | None = UASTNodeModel.nodes.get_or_none(uid=node_uid)
        if node is None:
            logger.warning("Node with uid %s not found", node_uid)
            return None

        if node.file_node_uid is None:
            logger.warning("Node with uid %s not have field 'file_node_uid", node_uid)
            return None

        source_bytes = GraphQuery.get_source_code_of_file(node.file_node_uid)
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8")

    @staticmethod
    def find_usage(node_uid: str) -> list[str] | None:
        """
        Find nodes that reference to this node
        Args:
            node_uid: this node's uid

        Returns:
            - ``list[node_id]`` of nodes that reference to this node.
            - ``None`` if node_uid is not found.
        """
        node: UASTNodeModel | None = UASTNodeModel.nodes.get_or_none(uid=node_uid)
        if node is None:
            return None

        refs_by: list[UASTNodeModel] = node.referenced_by.all()

        return [ref.uid for ref in refs_by]

    @staticmethod
    def find_callees(node_uid: str) -> list[str] | None:
        """
        Find nodes that this node or its children reference to.

        Args:
            node_uid:
        Returns:
            - ``list[node_id]`` of nodes that this node or its children reference to
            - ``None`` if node_uid is not found.
        """

        node: UASTNodeModel | None = UASTNodeModel.nodes.get_or_none(uid=node_uid)
        if node is None:
            return None

        result = []

        for r in cast(list[UASTNodeModel], node.references.all()):
            result.append(r.uid)

        for child in cast(list[UASTNodeModel], node.children.all()):
            child_callees = GraphQuery.find_callees(child.uid)
            if child_callees is not None:
                result += child_callees

        return result
