from fnmatch import fnmatch
from typing import Protocol, runtime_checkable

from tree_sitter import Node

from .build_context import BuildContext
from .node_builder import UASTNodeBuilder
from .types import CaptureType


@runtime_checkable
class CaptureHandler(Protocol):
    """
    Handle tree-sitter capture name, make it to a metadata or new-node-builder
        - metadata: not a node instance, it belongs to another node
        - new-node-builder: new node-builder
    """

    def handle(
        self,
        capture_name: CaptureType,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
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
    def __init__(self, capture_patterns: str | CaptureType | list[str | CaptureType]) -> None:
        """

        Args:
            capture_patterns: capture name or capture patterns. Can be a single value or a list
        """
        if isinstance(capture_patterns, str):
            self._capture_patterns = [capture_patterns]
        else:
            self._capture_patterns = capture_patterns

    def can_handle(
        self, capture_name: str, ts_child: Node, parent_builder: UASTNodeBuilder, context: BuildContext
    ) -> bool:
        """
        Check if  handler can handle this ts_node with given data.
        Args:
            capture_name:
            ts_child:
            parent_builder:
            context:

        Returns:

        """
        result = any([fnmatch(capture_name, pattern) for pattern in self._capture_patterns])
        return result

    def create_builder(
        self, capture_name: str, ts_child: Node, parent_builder: UASTNodeBuilder, context: BuildContext
    ) -> UASTNodeBuilder:
        """
        Create builder for ts_child
        Args:
            capture_name:
            ts_child:
            parent_builder:
            context:

        Returns:

        """
        builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
        builder.set_parent_id(parent_builder.id)
        return builder

    def do_after_build(
        self, builder: UASTNodeBuilder, ts_node: Node, parent_builder: UASTNodeBuilder, context: BuildContext
    ) -> None:
        """

        Args:
            builder: this current child node builder
            ts_node: this current tree-sitter node
            parent_builder: parent node builder
            context: build context(current scope is parent scope)

        Returns:

        """
        if builder.capture_name == "reference.type" and parent_builder.capture_name == "definition.parameter":
            parent_builder.set("data_type", context.get_text(ts_node))

    def handle(
        self, capture_name: str, ts_child: Node, parent_builder: UASTNodeBuilder, context: BuildContext
    ) -> bool | UASTNodeBuilder:
        if not self.can_handle(capture_name, ts_child, parent_builder, context):
            return False

        builder = self.create_builder(capture_name, ts_child, parent_builder, context)
        self.do_after_build(builder, ts_child, parent_builder, context)
        return builder


class BaseMetadataCaptureHandler(CaptureHandler):
    """
    To customize: override ``handle_{meta_name}`` method
    """

    def handle(
        self,
        capture_name: CaptureType,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        if not fnmatch(capture_name, "meta.*"):
            return False
        meta_type = capture_name.split(".")[-1]
        match meta_type:
            case "name":
                return self.handle_name(capture_name, ts_child, parent_builder, context)
            case "doc":
                return self.handle_docstring(capture_name, ts_child, parent_builder, context)
            case "module_path":
                return self.handle_module_path(capture_name, ts_child, parent_builder, context)
            case _:
                return False

    def handle_name(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
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

        parent_builder.set_name(context.get_text(ts_child))
        return True

    def handle_docstring(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
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
        parent_builder.set_docstring(context.get_text(ts_child))
        return True

    def handle_modifier(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_visibility(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_base_type(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_value(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_enum_value(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_decorator(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_module_path(
        self, capture_name: str, ts_child: Node, parent_builder: UASTNodeBuilder, context: BuildContext
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.module_path``: import module path
        Args:
            capture_name:
            ts_child:
            parent_builder:
            context:

        Returns:

        """
        text = context.get_text(ts_child)
        if parent_builder.capture_name == "dependency.import":
            parent_builder.set("module_path", text)
            parent_builder.set_name(text)
            return True
        return False

    def handle_alias(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        return False

    def handle_subject(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext | None = None,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.subject``: call subject
        Args:
            capture_name:
            ts_child:
            parent_builder:
            context:

        Returns:
        """
        if parent_builder.capture_name == "reference.call":
            parent_builder.set("subject", ts_child)

        return False
