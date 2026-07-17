"""
Module document.....
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from tree_sitter import Node, Query, QueryCursor, Tree

from .uast_node import UASTNode
from .uast_node_builder import CaptureType, UASTNodeBuilder, UASTNodeFactory


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


class CaptureHandler(Protocol):
    """
    Handle tree-sitter capture name, make it to a metadata or new-node-builder

        - metadata: not a node instance, it belongs to another node
        - new-node-builder: new node-builder
    """

    def handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        """
        Note: do not pop any Scope in context. Scope was manage by Converter

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
    @staticmethod
    def get_default_capture_priorities() -> dict[CaptureType, int]:
        return {"definition.method": 2, "definition.constructor": 1}

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
    capture_priorities: dict[CaptureType, int] = field(default_factory=get_default_capture_priorities)

    def get_capture_priorities(self, capture: CaptureType) -> int:
        return self.capture_priorities.get(capture, 100)


class BuildContext:
    class BuildScope:
        def __init__(self, builder: UASTNodeBuilder):
            self.builder = builder
            self.pending_metadata: dict[str, Any] = dict()
            self.state: dict[str, Any] = dict()

    def __init__(
        self, file_path: str | None = None, language_name: str | None = None, source_bytes: bytes | None = None
    ):
        self._file_path = file_path
        self._language_name = language_name
        self._source_bytes = source_bytes

        self._pending_ts_node_for_next_sibling: list[tuple[str, Node]] = []
        """In most case, use for stack metadata that will belong to next sibling node(in the same parent)"""

        self._scope: list[BuildContext.BuildScope] = []

    @property
    def file_path(self) -> str | None:
        return self._file_path

    @property
    def language_name(self) -> str | None:
        return self._language_name

    @property
    def source_bytes(self) -> bytes | None:
        return self._source_bytes

    def get_text(self, ts_node: Node) -> str | None:
        text_bytes = ts_node.text
        if text_bytes is not None:
            return text_bytes.decode("utf-8")
        elif self.source_bytes is not None:
            try:
                text_bytes = self.source_bytes[ts_node.start_byte : ts_node.end_byte]
                return text_bytes.decode("utf-8")
            except (IndexError, Exception):
                return None
        return None

    @property
    def current_scope(self) -> BuildContext.BuildScope:
        return self._scope[-1]

    def push_scope(self, scope: BuildContext.BuildScope) -> None:
        self._scope.append(scope)

    def pop_scope(self) -> BuildContext.BuildScope:
        return self._scope.pop()


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

        if not child_is_metadata and child_builder is None and ts_child.is_named:
            if context is not None:
                context.current_scope.pending_metadata.clear()

        if not child_is_metadata:
            # if child not is metadata, scan for it's children
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
