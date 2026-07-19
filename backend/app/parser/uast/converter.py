"""
Module document.....
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tree_sitter import Node, QueryCursor, Tree

from .adapter import LanguageAdapter
from .build_context import BuildContext
from .node import UASTNode
from .node_builder import UASTNodeBuilder


@runtime_checkable
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
            Root node of UAST tree. In most case, the result is instance of ``ContainerNode``.

        """
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
        # sort by priority
        for node_id, captures_name in captures_map.items():
            captures_name.sort(key=self.adapter.get_capture_priorities)

        root_builder = UASTNodeBuilder.from_ts_node(ts_root, "container.file")
        root_builder.set("path", file_path)
        root_builder.set("language", self.adapter.language_name)
        root_builder.set("source_bytes", source_bytes)

        build_context = BuildContext(
            file_path=file_path,
            language_name=self.adapter.language_name,
            source_bytes=source_bytes,
        )

        build_context.push_scope(BuildContext.BuildScope(root_builder))

        for child in ts_root.children:
            self.build_child_node(child, root_builder, captures_map, build_context)

        return root_builder.build(self.adapter.node_factory)

    def build_child_node(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        captures_map: dict[int, list[str]],
        context: BuildContext | None = None,
    ) -> None:
        captures = captures_map.get(ts_child.id, list())

        child_builder: UASTNodeBuilder | None = None
        child_is_metadata: bool = False

        for handler in self.adapter.handlers:
            for capture_name in captures:
                result = handler.handle(capture_name, ts_child, parent_builder, context)

                if isinstance(result, bool) and result:
                    # child node is metadata
                    # do not create new builder
                    child_is_metadata = True
                    break
                elif isinstance(result, UASTNodeBuilder):
                    # handler has created new builder for child node
                    child_builder = result

                    break
            if child_is_metadata or (child_builder is not None):
                break

        # Barrier, prevent metadata fall so depth.
        if (not child_is_metadata) and (child_builder is None) and ts_child.is_named:
            if context is not None:
                context.current_scope.pending_metadata.clear()

        if not child_is_metadata:
            next_builder: UASTNodeBuilder
            if child_builder is not None:
                next_builder = child_builder
                if context is not None:
                    child_scope = BuildContext.BuildScope(child_builder)
                    context.push_scope(child_scope)
            else:
                next_builder = parent_builder
            for child in ts_child.children:
                self.build_child_node(child, next_builder, captures_map, context)

        if child_builder is not None:
            new_child = child_builder.build(self.adapter.node_factory)
            if context is not None:
                context.pop_scope()
            parent_builder.add_child(new_child)
