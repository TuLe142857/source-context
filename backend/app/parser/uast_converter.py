from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tree_sitter import Node, Query, QueryCursor, Tree

from .uast_node import UastNode, UASTNodeBuilder, UASTNodeFactory


class UASTConverter(Protocol):
    """
    Use to convert tree-sitter tree to UAST tree.
    """

    def convert(self, tree: Tree, source_bytes: bytes, file_path: str | None = None) -> UastNode:
        """
        Convert tree-sitter tree to UAST(Unified Abstract Syntax) tree.
        Args:
            tree: tree-sitter tree.builders_stack.pop()
            source_bytes: source code as bytes.
            file_path: file path, use to add more information to the output nodes. Defaults to None

        Returns: root node of UAST tree. In most case, the result is instance of FileNode.

        """
        pass


class CaptureHandler(Protocol):
    def handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        """

        Args:
            capture_name:
            ts_child: tree-sitter child node
            parent_builder: UASTBuilder of parent node
            context: build context

        Returns: boolean or UASTNodeBuilder
            - true: child node was handled and become metadata of parent node
            - false: childe node was not handled
            - builder: child node was handled and become new node, return buider of this node. This buider must be
              continued bulding with its children

        """
        pass


@dataclass(frozen=True, kw_only=True)
class LanguageAdapter:
    language_name: str
    query: Query
    node_factory: UASTNodeFactory
    handlers: list[CaptureHandler]


@dataclass
class BuildContext:
    pass


class BaseUASTConverter(UASTConverter):
    def __init__(self, adapter: LanguageAdapter):
        self.adapter = adapter

    def convert(self, tree: Tree, source_bytes: bytes, file_path: str | None = None) -> UastNode:
        ts_root = tree.root_node
        query_result: dict[str, list[Node]] = QueryCursor(self.adapter.query).captures(ts_root)
        captures_map: dict[int, list[str]] = dict()
        for capture_name, nodes in query_result.items():
            for node in nodes:
                if node.id not in captures_map:
                    captures_map[node.id] = list()
                captures_map[node.id].append(capture_name)
        root_builder = UASTNodeBuilder.from_ts_node(ts_root, "definition.file")

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

        for capture_name in captures:
            for handler in self.adapter.handlers:
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
