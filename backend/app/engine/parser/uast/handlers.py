from fnmatch import fnmatch
from typing import Protocol, runtime_checkable

from tree_sitter import Node

from .build_context import BuildContext
from .node_builder import UASTNodeBuilder
from .types import (
    CaptureType,
    is_type_def_capture,
    is_function_like_capture,
    is_variable_like_capture,
    is_definition_capture,
    is_dependency_capture,
)


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
    def __init__(
        self, capture_patterns: str | CaptureType | list[str | CaptureType]
    ) -> None:
        """

        Args:
            capture_patterns: capture name or capture patterns. Can be a single value or a list
        """
        if isinstance(capture_patterns, str):
            self._capture_patterns = [capture_patterns]
        else:
            self._capture_patterns = capture_patterns

    def can_handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
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
        result = any(
            [fnmatch(capture_name, pattern) for pattern in self._capture_patterns]
        )
        return result

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
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
        self,
        builder: UASTNodeBuilder,
        ts_node: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> None:
        """

        Args:
            builder: this current child node builder
            ts_node: this current tree-sitter node
            parent_builder: parent node builder
            context: build context(current scope is parent scope)

        Returns:

        """
        if builder.capture_name == "reference.type":
            BaseMetadataCaptureHandler.set_type_attribute(
                parent_builder, context.get_text(ts_node)
            )

    def handle(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
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

    _MODIFIER_FLAG_MAP: dict[str, str] = {
        "static": "is_static",
        "abstract": "is_abstract",
        "async": "is_async",
        "override": "is_override",
    }
    """Modifier tokens shared across languages that map to a boolean flag on a
    function-like definition. Override per-adapter for language-specific tokens."""

    _VISIBILITY_MODIFIERS: frozenset[str] = frozenset(
        {"public", "private", "protected"}
    )
    """Modifier tokens that double as visibility (e.g. Java's public/private/protected)."""

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
                return self.handle_name(ts_child, parent_builder, context)
            case "doc":
                return self.handle_docstring(ts_child, parent_builder, context)
            case "module_path":
                return self.handle_module_path(ts_child, parent_builder, context)
            case "modifier":
                return self.handle_modifier(ts_child, parent_builder, context)
            case "visibility":
                return self.handle_visibility(ts_child, parent_builder, context)
            case "base_type":
                return self.handle_base_type(ts_child, parent_builder, context)
            case "type":
                return self.handle_type(ts_child, parent_builder, context)
            case "value":
                return self.handle_value(ts_child, parent_builder, context)
            case "enum_value":
                return self.handle_enum_value(ts_child, parent_builder, context)
            case "decorator":
                return self.handle_decorator(ts_child, parent_builder, context)
            case "alias":
                return self.handle_alias(ts_child, parent_builder, context)
            case "subject":
                return self.handle_subject(ts_child, parent_builder, context)
            case _:
                return False

    def handle_name(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.name``
        """

        parent_builder.set_name(context.get_text(ts_child))
        return True

    def handle_docstring(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.doc``
        """
        parent_builder.set_docstring(context.get_text(ts_child))
        return True

    def handle_modifier(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.modifier``: appends the raw token to ``modifiers`` on any
        definition, and additionally infers ``visibility`` (public/private/protected)
        or a boolean flag (``is_static``/``is_abstract``/``is_async``/``is_override``)
        for tokens shared across languages. Override ``_MODIFIER_FLAG_MAP``/
        ``_VISIBILITY_MODIFIERS`` for language-specific tokens.
        """

        if not is_definition_capture(parent_builder.capture_name):
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.append("modifiers", text)
        if text in self._VISIBILITY_MODIFIERS:
            parent_builder.set("visibility", text)
        elif text in self._MODIFIER_FLAG_MAP:
            flag_name = self._MODIFIER_FLAG_MAP[text]
            # is_abstract exists on both FunctionNode and TypeDefinitionNode
            # (e.g. "abstract class"); the other flags are function-only.
            applies_to_type_definition = (
                flag_name == "is_abstract"
                and is_type_def_capture(parent_builder.capture_name)
            )
            if (
                is_function_like_capture(parent_builder.capture_name)
                or applies_to_type_definition
            ):
                parent_builder.set(flag_name, True)
        return True

    def handle_visibility(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Handle ``@meta.visibility``: sets ``visibility`` on any definition."""
        if not is_definition_capture(parent_builder.capture_name):
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.set("visibility", text)
        return True

    def handle_base_type(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Handle ``@meta.base_type``: appends to ``base_types`` on a type definition."""
        if not is_type_def_capture(parent_builder.capture_name):
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.append("base_types", text)
        return True

    def handle_type(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.type``: ``return_type`` for a function-like parent, or
        ``data_type`` for a variable-like parent.
        """
        return BaseMetadataCaptureHandler.set_type_attribute(
            parent_builder, context.get_text(ts_child)
        )

    def handle_value(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Handle ``@meta.value``: sets ``initial_value`` on a variable-like parent."""
        if not is_variable_like_capture(parent_builder.capture_name):
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.set("initial_value", text)
        return True

    def handle_enum_value(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Handle ``@meta.enum_value``: appends to ``enum_values`` on an enum definition."""
        if parent_builder.capture_name != "definition.enum":
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.append("enum_values", text)
        return True

    def handle_decorator(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Handle ``@meta.decorator``: appends to ``decorators`` on any definition."""
        if not is_definition_capture(parent_builder.capture_name):
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.append("decorators", text)
        return True

    def handle_module_path(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.module_path``: import module path
        """
        text = context.get_text(ts_child)
        if parent_builder.capture_name == "dependency.import":
            parent_builder.set("module_path", text)
            parent_builder.set_name(text)
            return True
        return False

    def handle_alias(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """
        Handle ``@meta.alias``: alias name for an import/export.

        Without a per-symbol ``@meta.name``/``@meta.alias`` pairing from the query,
        this stores the alias keyed by the import/export node's current ``name``
        (or ``"*"`` if unset). Languages aliasing multiple symbols per statement
        (e.g. ``from an import b as c, d as e``) should override this to pair each
        alias with its correct imported name.
        """
        if not is_dependency_capture(parent_builder.capture_name):
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        alias_map = parent_builder.attributes_map.setdefault("alias", {})
        alias_map[parent_builder.name or "*"] = text
        return True

    def handle_subject(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Handle ``@meta.subject``: sets ``subject`` on a call reference."""
        if parent_builder.capture_name != "reference.call":
            return False
        text = context.get_text(ts_child)
        if text is None:
            return False
        parent_builder.set("subject", text)
        return True

    @staticmethod
    def set_type_attribute(parent_builder: UASTNodeBuilder, text: str | None) -> bool:
        """
        Route a type-like capture (``@meta.type`` / ``@reference.type``) to the correct
        attribute depending on what kind of definition the parent is: ``return_type``
        for function-like parents, ``data_type`` for variable-like parents.

        Returns:
            Whether the parent matched a known target and was updated.
        """
        if is_function_like_capture(parent_builder.capture_name):
            parent_builder.set("return_type", text)
            return True
        if is_variable_like_capture(parent_builder.capture_name):
            parent_builder.set("data_type", text)
            return True
        return False
