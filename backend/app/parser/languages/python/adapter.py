"""Tree-sitter adapter and capture handlers for Python."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import tree_sitter_python
from tree_sitter import Language, Node, Query

from app.parser.uast import (
    BaseMetadataCaptureHandler,
    BaseNodeCaptureHandler,
    BuildContext,
    LanguageAdapter,
    UASTNodeBuilder,
)


_PENDING_DECORATORS_KEY = "python.pending_decorators"


@lru_cache
def get_language() -> Language:
    """Return the cached Python Tree-sitter language."""

    return Language(
        tree_sitter_python.language(),
    )


@lru_cache
def get_query_str() -> str:
    """Load the Python UAST query from disk."""

    query_path = Path(__file__).parent / "query.scm"

    if not query_path.is_file():
        raise RuntimeError(
            f"Cannot load Python query: {query_path}",
        )

    return query_path.read_text(
        encoding="utf-8",
    )


@lru_cache
def get_query() -> Query:
    """Compile and cache the Python UAST query."""

    return Query(
        get_language(),
        get_query_str(),
    )


class PythonMetadataCaptureHandler(
    BaseMetadataCaptureHandler,
):
    """Handle Python metadata requiring cross-sibling state."""

    def handle_decorator(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Store a decorator until its following definition is built."""

        del parent_builder

        decorator_text = context.get_text(ts_child)

        if decorator_text is None:
            return False

        pending_decorators = context.current_scope.pending_metadata.setdefault(
            _PENDING_DECORATORS_KEY,
            [],
        )

        if not isinstance(pending_decorators, list):
            pending_decorators = []
            context.current_scope.pending_metadata[_PENDING_DECORATORS_KEY] = (
                pending_decorators
            )

        pending_decorators.append(
            decorator_text.strip(),
        )

        return True


class PythonDefinitionCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build Python classes and function-like definitions."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns="definition.*",
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Create a definition builder and extract common fields."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        name_node = ts_child.child_by_field_name(
            "name",
        )

        if name_node is not None:
            builder.set_name(
                context.get_text(name_node),
            )

        self._apply_pending_decorators(
            builder,
            context,
        )

        if capture_name == "definition.class":
            self._apply_base_types(
                builder,
                ts_child,
                context,
            )

        if capture_name in {
            "definition.function",
            "definition.method",
            "definition.constructor",
        }:
            self._apply_function_metadata(
                builder,
                ts_child,
                context,
            )

        return builder

    @staticmethod
    def _apply_pending_decorators(
        builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> None:
        pending_decorators: Any = context.current_scope.pending_metadata.pop(
            _PENDING_DECORATORS_KEY,
            [],
        )

        if not isinstance(pending_decorators, list):
            return

        for decorator in pending_decorators:
            if isinstance(decorator, str):
                builder.append(
                    "decorators",
                    decorator,
                )

    @staticmethod
    def _apply_base_types(
        builder: UASTNodeBuilder,
        ts_child: Node,
        context: BuildContext,
    ) -> None:
        superclasses_node = ts_child.child_by_field_name(
            "superclasses",
        )

        if superclasses_node is None:
            return

        for base_node in superclasses_node.named_children:
            # metaclass=ABCMeta is configuration metadata,
            # not a normal inheritance base.
            if base_node.type == "keyword_argument":
                continue

            base_type = context.get_text(base_node)

            if base_type is not None:
                builder.append(
                    "base_types",
                    base_type,
                )

    @staticmethod
    def _apply_function_metadata(
        builder: UASTNodeBuilder,
        ts_child: Node,
        context: BuildContext,
    ) -> None:
        return_type_node = ts_child.child_by_field_name(
            "return_type",
        )

        if return_type_node is not None:
            builder.set(
                "return_type",
                context.get_text(return_type_node),
            )

        is_async = any(child.type == "async" for child in ts_child.children)

        if is_async:
            builder.set(
                "is_async",
                True,
            )


class PythonParameterCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build Python parameter nodes from binding syntax."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns="definition.parameter",
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Extract parameter name, type and default value."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        binding_node = self._get_binding_node(
            ts_child,
        )

        if binding_node is not None:
            binding_text = context.get_text(
                binding_node,
            )

            if binding_text is not None:
                builder.set_name(
                    binding_text.lstrip("*"),
                )

        type_node = ts_child.child_by_field_name(
            "type",
        )

        if type_node is not None:
            builder.set(
                "data_type",
                context.get_text(type_node),
            )

        value_node = ts_child.child_by_field_name(
            "value",
        )

        if value_node is not None:
            builder.set(
                "initial_value",
                context.get_text(value_node),
            )

        return builder

    @staticmethod
    def _get_binding_node(
        ts_child: Node,
    ) -> Node | None:
        if ts_child.type == "identifier":
            return ts_child

        name_node = ts_child.child_by_field_name(
            "name",
        )

        if name_node is not None:
            return name_node

        type_node = ts_child.child_by_field_name(
            "type",
        )

        for named_child in ts_child.named_children:
            if type_node is not None and named_child.id == type_node.id:
                continue

            return named_child

        return None


class PythonVariableCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build Python variable definitions from assignment nodes."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns="definition.variable",
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Extract variable name, annotation and initial value."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        left_node = ts_child.child_by_field_name(
            "left",
        )

        if left_node is not None:
            builder.set_name(
                context.get_text(left_node),
            )

        type_node = ts_child.child_by_field_name(
            "type",
        )

        if type_node is not None:
            builder.set(
                "data_type",
                context.get_text(type_node),
            )

        right_node = ts_child.child_by_field_name(
            "right",
        )

        if right_node is not None:
            builder.set(
                "initial_value",
                context.get_text(right_node),
            )

        return builder


class PythonCallCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build Python call references and their receiver subject."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns="reference.call",
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Extract callable name and attribute receiver."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        function_node = ts_child.child_by_field_name(
            "function",
        )

        if function_node is None:
            return builder

        if function_node.type == "attribute":
            name_node = function_node.child_by_field_name(
                "attribute",
            )
            subject_node = function_node.child_by_field_name(
                "object",
            )

            if name_node is not None:
                builder.set_name(
                    context.get_text(name_node),
                )

            if subject_node is not None:
                builder.set(
                    "subject",
                    context.get_text(subject_node),
                )

            return builder

        builder.set_name(
            context.get_text(function_node),
        )

        return builder


class PythonAttributeCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build Python attribute-access references."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns="reference.attribute",
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Extract the accessed attribute name."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        attribute_node = ts_child.child_by_field_name(
            "attribute",
        )

        if attribute_node is not None:
            builder.set_name(
                context.get_text(attribute_node),
            )

        return builder


class PythonAdapter(LanguageAdapter):
    """Convert Python Tree-sitter captures into UAST nodes."""

    def __init__(self) -> None:
        super().__init__(
            language_name="python",
            query=get_query(),
            handlers=[
                PythonMetadataCaptureHandler(),
                PythonParameterCaptureHandler(),
                PythonVariableCaptureHandler(),
                PythonCallCaptureHandler(),
                PythonAttributeCaptureHandler(),
                PythonDefinitionCaptureHandler(),
                BaseNodeCaptureHandler(
                    capture_patterns=[
                        "reference.type",
                        "dependency.*",
                    ],
                ),
            ],
        )


@lru_cache
def get_adapter() -> LanguageAdapter:
    """Return the cached Python language adapter."""

    return PythonAdapter()
