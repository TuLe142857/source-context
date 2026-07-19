from fnmatch import fnmatch
from typing import Protocol, runtime_checkable

from tree_sitter import Node

from .build_context import BuildContext
from .node_builder import UASTNodeBuilder


@runtime_checkable
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


class BaseNodeCaptureHandler(CaptureHandler):
    def __init__(self, capture_patterns: str | list[str]) -> None:
        if isinstance(capture_patterns, str):
            self._capture_patterns = [capture_patterns]
        else:
            self._capture_patterns = capture_patterns

    def match(self, capture_name: str) -> bool:
        result = any([fnmatch(capture_name, pattern) for pattern in self._capture_patterns])
        return result

    def __handle__(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
        builder.set_parent_id(parent_builder.id)
        return builder

    def handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        if not self.match(capture_name):
            return False
        return self.__handle__(capture_name, ts_child, parent_builder, context)


class BaseMetadataCaptureHandler(CaptureHandler):
    """
    To customize: override ``handle_{meta_name}`` method
    """

    def handle_name(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.name``
        Args:
            capture_name:
            ts_child:
            parent_builder:
            context:

        Returns:

        """
        if context is not None:
            parent_builder.set_name(context.get_text(ts_child))
        return True

    def handle_docstring(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.doc``
        Args:
            capture_name:
            ts_child:
            parent_builder:
            context:

        Returns:

        """
        if context is not None:
            parent_builder.set_docstring(context.get_text(ts_child))
        return True

    def handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        if not fnmatch(capture_name, "meta.*"):
            return False
        meta_type = capture_name.split(".")[-1]
        match meta_type:
            case "name":
                return self.handle_name(capture_name, ts_child, parent_builder, context)
            case "doc":
                return self.handle_docstring(capture_name, ts_child, parent_builder, context)
            case _:
                return False
