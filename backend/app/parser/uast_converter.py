"""
Module document.....
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tree_sitter import Node, Query, QueryCursor, Tree

from .uast_node import UASTNode, UASTNodeBuilder, UASTNodeFactory


class UASTConverter(Protocol):
    """
    Use to convert tree-sitter tree to UAST tree.
    """

    def convert(self, tree: Tree, source_bytes: bytes, file_path: str | None = None) -> UASTNode:
        """
        Convert tree-sitter tree to UAST(Unified Abstract Syntax) tree.

        Args:
            tree: tree-sitter Tree object.
            source_bytes: source code as bytes.
            file_path: file path, use to add more information to the output nodes. Defaults to None.

        Returns:
            Root node of UAST tree. In most case, the result is instance of FileNode.

        """
        pass


class CaptureHandler(Protocol):
    """
    Handle tree-sitter capture name, make it to a metadata or new-node-builder

        - ``metadata``: not a node instance, it belongs to another node
        - ``new-node-builder``: new node-builder
    """

    def handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        """

        Args:
            capture_name: tree-sitter-query capture
            ts_child: tree-sitter child node
            parent_builder: UASTBuilder of parent node
            context: build context

        Returns:
            Boolean or UASTNodeBuilder

                - ``True``: child node was handled and become metadata of parent node
                - ``False``: childe node was not handled
                - ``UASTNodeBuilder``: child node was handled and become new node, return buider of this node. This
                  buider must be continued bulding with its children.

        """
        pass


class DefaultCaptureHandler:
    @staticmethod
    def get_default_handler() -> list[CaptureHandler]:
        return [
            DefaultCaptureHandler.ContainerHandler(),
            DefaultCaptureHandler.DependencyHandler(),
            DefaultCaptureHandler.DefinitionHandler(),
            DefaultCaptureHandler.MetadataHandler(),
            DefaultCaptureHandler.ReferenceHandler(),
        ]

    class DefinitionHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("definition"):
                return False

            if parent_builder.capture_name == "definition.class" and capture_name == "definition.function":
                capture_name = "definition.method"

            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            return builder

    class ReferenceHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("reference"):
                return False
            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            return builder

    class DependencyHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("dependency"):
                return False
            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            return builder

    class MetadataHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("meta"):
                return False
            meta_type = capture_name.split(".")[-1]

            text_bytes = ts_child.text
            text = text_bytes.decode("utf-8") if text_bytes is not None else ""

            match meta_type:
                case "name":
                    parent_builder.set_name(text)
                case "doc":
                    parent_builder.set_docstring(text)
                case "comment":
                    pass
                case "visibility":
                    pass
                case "modifier":
                    pass
                case "decorator":
                    pass
                case "return_type":
                    pass
                case "type":
                    pass
                case "base_type":
                    pass
                case "value":
                    pass
                case "init_value":
                    pass
                case _:
                    pass

            return True

    class ContainerHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("container"):
                return False
            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            return builder


@dataclass(frozen=True, kw_only=True)
class LanguageAdapter:
    """

    Attributes:
        language_name:
        query:
        node_factory:
        handlers:

    """

    language_name: str
    query: Query
    node_factory: UASTNodeFactory
    handlers: list[CaptureHandler]


@dataclass
class BuildContext:
    pass


class BaseUASTConverter(UASTConverter):
    """
    Implement ``DFS`` to convert tree-sitter tree to UAST tree.
    """

    def __init__(self, adapter: LanguageAdapter):
        self.adapter = adapter

    def convert(self, tree: Tree, source_bytes: bytes, file_path: str | None = None) -> UASTNode:
        ts_root = tree.root_node
        query_result: dict[str, list[Node]] = QueryCursor(self.adapter.query).captures(ts_root)
        captures_map: dict[int, list[str]] = dict()
        for capture_name, nodes in query_result.items():
            for node in nodes:
                if node.id not in captures_map:
                    captures_map[node.id] = list()
                captures_map[node.id].append(capture_name)
        root_builder = UASTNodeBuilder.from_ts_node(ts_root, "container.file")

        for child in ts_root.children:
            self.build_child_node(child, root_builder, captures_map)

        return root_builder.build(self.adapter.node_factory)

    def build_child_node(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        captures_map: dict[int, list[str]],
    ) -> None:
        captures = captures_map.get(ts_child.id, list())

        child_builder: UASTNodeBuilder | None = None
        child_is_metadata: bool = False

        for handler in self.adapter.handlers:
            for capture_name in captures:
                result = handler.handle(capture_name, ts_child, parent_builder)
                if isinstance(result, bool):
                    if result:
                        child_is_metadata = True
                        break
                if isinstance(result, UASTNodeBuilder):
                    child_builder = result

        if not child_is_metadata:
            next_builder = child_builder if child_builder is not None else parent_builder
            for child in ts_child.children:
                self.build_child_node(child, next_builder, captures_map)

        if child_builder is not None:
            new_child = child_builder.build(self.adapter.node_factory)
            parent_builder.add_child(new_child)
