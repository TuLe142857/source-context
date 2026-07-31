"""Tree-sitter adapter and capture handlers for JavaScript and JSX."""

from functools import lru_cache
from pathlib import Path

import tree_sitter_javascript
from tree_sitter import Language, Node, Query

from app.parser.uast import (
    BaseMetadataCaptureHandler,
    BaseNodeCaptureHandler,
    BuildContext,
    LanguageAdapter,
    UASTNodeBuilder,
)


_PENDING_DOC_KEY = "javascript.pending_doc"

_FUNCTION_VALUE_NODE_TYPES = {
    "arrow_function",
    "function_expression",
    "generator_function",
}


@lru_cache
def get_language() -> Language:
    """Return the cached JavaScript Tree-sitter language."""

    return Language(
        tree_sitter_javascript.language(),
    )


@lru_cache
def get_query_str() -> str:
    """Load the JavaScript UAST query."""

    query_path = Path(__file__).parent / "query.scm"

    if not query_path.is_file():
        raise RuntimeError(
            f"Cannot load JavaScript query: {query_path}",
        )

    return query_path.read_text(
        encoding="utf-8",
    )


@lru_cache
def get_query() -> Query:
    """Compile and cache the JavaScript UAST query."""

    return Query(
        get_language(),
        get_query_str(),
    )


def _strip_string_quotes(value: str) -> str:
    """Remove matching JavaScript string delimiters."""

    if len(value) < 2:
        return value

    quote = value[0]

    if quote in {"'", '"', "`"} and value[-1] == quote:
        return value[1:-1]

    return value


class JavaScriptMetadataCaptureHandler(
    BaseMetadataCaptureHandler,
):
    """Handle metadata requiring JavaScript sibling context."""

    def handle_docstring(
        self,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> bool | UASTNodeBuilder:
        """Store a JSDoc comment for the following definition."""

        del parent_builder

        docstring = context.get_text(ts_child)

        if docstring is None:
            return False

        context.current_scope.pending_metadata[_PENDING_DOC_KEY] = docstring

        return True


class JavaScriptDefinitionCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build JavaScript classes and function-like definitions."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns=[
                "definition.class",
                "definition.function",
                "definition.method",
                "definition.constructor",
            ],
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Create a definition builder and extract common metadata."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        name_node = self._get_name_node(ts_child)

        if name_node is not None:
            builder.set_name(
                context.get_text(name_node),
            )

        self._apply_pending_docstring(
            builder,
            context,
        )

        if capture_name == "definition.class":
            self._apply_base_types(
                builder,
                ts_child,
                context,
            )
        else:
            self._apply_function_metadata(
                builder,
                ts_child,
                context,
            )

        return builder

    @staticmethod
    def _get_name_node(
        ts_child: Node,
    ) -> Node | None:
        """Return the name node for declarations and class fields."""

        name_node = ts_child.child_by_field_name(
            "name",
        )

        if name_node is not None:
            return name_node

        return ts_child.child_by_field_name(
            "property",
        )

    @staticmethod
    def _apply_pending_docstring(
        builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> None:
        docstring = context.current_scope.pending_metadata.pop(
            _PENDING_DOC_KEY,
            None,
        )

        if isinstance(docstring, str):
            builder.set_docstring(
                docstring,
            )

    @staticmethod
    def _apply_base_types(
        builder: UASTNodeBuilder,
        ts_child: Node,
        context: BuildContext,
    ) -> None:
        for child in ts_child.named_children:
            if child.type != "class_heritage":
                continue

            for base_node in child.named_children:
                base_type = context.get_text(
                    base_node,
                )

                if base_type is not None:
                    builder.append(
                        "base_types",
                        base_type,
                    )

    @classmethod
    def _apply_function_metadata(
        cls,
        builder: UASTNodeBuilder,
        ts_child: Node,
        context: BuildContext,
    ) -> None:
        function_node = cls._get_function_node(
            ts_child,
        )

        if function_node is not ts_child:
            name_node = cls._get_name_node(
                ts_child,
            )

            if name_node is not None:
                builder.set_name(
                    context.get_text(name_node),
                )

        if cls._contains_token(
            ts_child,
            "static",
        ):
            builder.set(
                "is_static",
                True,
            )
            builder.append(
                "modifiers",
                "static",
            )

        if cls._contains_token(
            function_node,
            "async",
        ):
            builder.set(
                "is_async",
                True,
            )
            builder.append(
                "modifiers",
                "async",
            )

        if "generator" in function_node.type or cls._contains_token(
            function_node,
            "*",
        ):
            builder.set(
                "is_generator",
                True,
            )

        for modifier in ("get", "set"):
            if cls._contains_token(
                ts_child,
                modifier,
            ):
                builder.append(
                    "modifiers",
                    modifier,
                )

    @staticmethod
    def _get_function_node(
        ts_child: Node,
    ) -> Node:
        if ts_child.type in {
            "variable_declarator",
            "field_definition",
        }:
            value_node = ts_child.child_by_field_name(
                "value",
            )

            if value_node is not None:
                return value_node

        return ts_child

    @staticmethod
    def _contains_token(
        node: Node,
        token_type: str,
    ) -> bool:
        return any(child.type == token_type for child in node.children)


class JavaScriptParameterCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build JavaScript function parameter nodes."""

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
        """Extract parameter binding and default value."""

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
            builder.set_name(
                context.get_text(binding_node),
            )

        value_node = ts_child.child_by_field_name(
            "right",
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
        if ts_child.type in {
            "identifier",
            "object_pattern",
            "array_pattern",
        }:
            return ts_child

        left_node = ts_child.child_by_field_name(
            "left",
        )

        if left_node is not None:
            return left_node

        for child in ts_child.named_children:
            return child

        return None


class JavaScriptVariableCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Classify JavaScript variable declarators and class fields."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns=[
                "definition.variable",
                "definition.field",
            ],
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Build a function, constant, variable, field or field method."""

        effective_capture_name = self._resolve_definition_capture(
            ts_child,
            capture_name,
        )

        builder = UASTNodeBuilder.from_ts_node(
            ts_child,
            effective_capture_name,
        )
        builder.set_parent_id(
            parent_builder.id,
        )

        name_node = self._get_name_node(
            ts_child,
        )

        if name_node is not None:
            builder.set_name(
                context.get_text(name_node),
            )

        value_node = ts_child.child_by_field_name(
            "value",
        )

        if effective_capture_name in {
            "definition.function",
            "definition.method",
        }:
            JavaScriptDefinitionCaptureHandler._apply_function_metadata(
                builder,
                ts_child,
                context,
            )
        elif value_node is not None:
            builder.set(
                "initial_value",
                context.get_text(value_node),
            )

        return builder

    @classmethod
    def _resolve_definition_capture(
        cls,
        ts_child: Node,
        original_capture_name: str,
    ) -> str:
        """Resolve the semantic definition kind from the initializer."""

        value_node = ts_child.child_by_field_name(
            "value",
        )

        if value_node is not None and value_node.type in _FUNCTION_VALUE_NODE_TYPES:
            if ts_child.type == "field_definition":
                return "definition.method"

            return "definition.function"

        if ts_child.type == "field_definition":
            return "definition.field"

        if cls._is_const_declaration(ts_child):
            return "definition.constant"

        return original_capture_name

    @staticmethod
    def _get_name_node(
        ts_child: Node,
    ) -> Node | None:
        """Return the binding/property node representing the name."""

        name_node = ts_child.child_by_field_name(
            "name",
        )

        if name_node is not None:
            return name_node

        return ts_child.child_by_field_name(
            "property",
        )

    @staticmethod
    def _is_const_declaration(
        ts_child: Node,
    ) -> bool:
        """Return whether a variable declarator belongs to const."""

        parent = ts_child.parent

        if parent is None or parent.type != "lexical_declaration":
            return False

        return any(child.type == "const" for child in parent.children)


class JavaScriptDependencyCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build ES module and CommonJS dependencies."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns="dependency.import",
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Extract the imported module path."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        source_node = ts_child.child_by_field_name(
            "source",
        )

        if source_node is None and ts_child.type == "call_expression":
            arguments_node = ts_child.child_by_field_name(
                "arguments",
            )

            if arguments_node is not None:
                source_node = next(
                    (
                        child
                        for child in arguments_node.named_children
                        if child.type == "string"
                    ),
                    None,
                )

        if source_node is None:
            return builder

        source_text = context.get_text(
            source_node,
        )

        if source_text is None:
            return builder

        module_path = _strip_string_quotes(
            source_text,
        )

        builder.set(
            "module_path",
            module_path,
        )
        builder.set_name(
            module_path,
        )

        return builder


class JavaScriptCallCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build function, member and constructor calls."""

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
        """Extract callable name and receiver subject."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        callable_node = ts_child.child_by_field_name(
            "function",
        )

        if callable_node is None:
            callable_node = ts_child.child_by_field_name(
                "constructor",
            )

        if callable_node is None:
            return builder

        self._apply_callable(
            builder,
            callable_node,
            context,
        )

        return builder

    @staticmethod
    def _apply_callable(
        builder: UASTNodeBuilder,
        callable_node: Node,
        context: BuildContext,
    ) -> None:
        if callable_node.type == "member_expression":
            subject_node = callable_node.child_by_field_name(
                "object",
            )
            name_node = callable_node.child_by_field_name(
                "property",
            )

            if subject_node is not None:
                builder.set(
                    "subject",
                    context.get_text(subject_node),
                )

            if name_node is not None:
                builder.set_name(
                    context.get_text(name_node),
                )

            return

        if callable_node.type == "subscript_expression":
            subject_node = callable_node.child_by_field_name(
                "object",
            )
            index_node = callable_node.child_by_field_name(
                "index",
            )

            if subject_node is not None:
                builder.set(
                    "subject",
                    context.get_text(subject_node),
                )

            if index_node is not None:
                builder.set_name(
                    context.get_text(index_node),
                )

            return

        builder.set_name(
            context.get_text(callable_node),
        )


class JavaScriptAttributeCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build JavaScript attribute-access references."""

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
        """Extract attribute name and receiver metadata."""

        builder = super().create_builder(
            capture_name,
            ts_child,
            parent_builder,
            context,
        )

        subject_node = ts_child.child_by_field_name(
            "object",
        )

        name_node = ts_child.child_by_field_name(
            "property",
        )

        if name_node is None:
            name_node = ts_child.child_by_field_name(
                "index",
            )

        if subject_node is not None:
            builder.set_metadata(
                "subject",
                context.get_text(subject_node),
            )

        if name_node is not None:
            builder.set_name(
                context.get_text(name_node),
            )

        return builder


class JavaScriptAdapter(LanguageAdapter):
    """Convert JavaScript and JSX captures into UAST nodes."""

    def __init__(self) -> None:
        super().__init__(
            language_name="javascript",
            query=get_query(),
            handlers=[
                JavaScriptMetadataCaptureHandler(),
                JavaScriptDependencyCaptureHandler(),
                JavaScriptParameterCaptureHandler(),
                JavaScriptVariableCaptureHandler(),
                JavaScriptDefinitionCaptureHandler(),
                JavaScriptCallCaptureHandler(),
                JavaScriptAttributeCaptureHandler(),
            ],
            capture_priorities={
                "definition.constructor": 1,
                "dependency.import": 2,
                "definition.method": 3,
                "definition.function": 4,
                "definition.constant": 5,
                "definition.field": 6,
                "definition.variable": 7,
                "definition.parameter": 8,
                "reference.call": 20,
                "reference.attribute": 30,
            },
        )


@lru_cache
def get_adapter() -> LanguageAdapter:
    """Return the cached JavaScript adapter."""

    return JavaScriptAdapter()
