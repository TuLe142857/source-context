"""Tree-sitter adapters and semantic handlers for TypeScript and TSX."""

from functools import lru_cache
from pathlib import Path
import re

import tree_sitter_typescript
from tree_sitter import Language, Node, Query

from app.parser.languages.javascript.adapter import (
    JavaScriptAttributeCaptureHandler,
    JavaScriptCallCaptureHandler,
    JavaScriptDefinitionCaptureHandler,
    JavaScriptDependencyCaptureHandler,
    JavaScriptMetadataCaptureHandler,
)
from app.parser.uast import (
    BaseNodeCaptureHandler,
    BuildContext,
    LanguageAdapter,
    UASTNodeBuilder,
)


_FUNCTION_VALUE_NODE_TYPES = {
    "arrow_function",
    "function_expression",
    "generator_function",
}

_VISIBILITY_MODIFIERS = {
    "public",
    "private",
    "protected",
}

_SYMBOL_MODIFIERS = {
    "abstract",
    "declare",
    "override",
    "readonly",
    "static",
}


@lru_cache
def get_typescript_language() -> Language:
    """Return the plain TypeScript Tree-sitter language."""

    return Language(
        tree_sitter_typescript.language_typescript(),
    )


@lru_cache
def get_tsx_language() -> Language:
    """Return the JSX-aware TypeScript Tree-sitter language."""

    return Language(
        tree_sitter_typescript.language_tsx(),
    )


@lru_cache
def get_query_str() -> str:
    """Load the shared TypeScript and TSX UAST query."""

    query_path = Path(__file__).parent / "query.scm"

    if not query_path.is_file():
        raise RuntimeError(
            f"Cannot load TypeScript query: {query_path}",
        )

    return query_path.read_text(
        encoding="utf-8",
    )


@lru_cache
def get_typescript_query() -> Query:
    """Compile the UAST query against plain TypeScript."""

    return Query(
        get_typescript_language(),
        get_query_str(),
    )


@lru_cache
def get_tsx_query() -> Query:
    """Compile the UAST query against TSX."""

    return Query(
        get_tsx_language(),
        get_query_str(),
    )


def _get_node_text(
    context: BuildContext,
    node: Node | None,
) -> str | None:
    """Return stripped source text for a Tree-sitter node."""

    if node is None:
        return None

    text = context.get_text(node)

    if text is None:
        return None

    return text.strip()


def _strip_type_annotation(
    value: str,
) -> str:
    """Remove the leading colon from a type_annotation node."""

    value = value.strip()

    if value.startswith(":"):
        return value[1:].strip()

    return value


def _get_type_text(
    node: Node,
    context: BuildContext,
) -> str | None:
    """Extract and normalize the type field of a TS node."""

    type_node = node.child_by_field_name(
        "type",
    )

    type_text = _get_node_text(
        context,
        type_node,
    )

    if type_text is None:
        return None

    return _strip_type_annotation(
        type_text,
    )


def _get_name_node(
    node: Node,
) -> Node | None:
    """Return the semantic name or binding node."""

    for field_name in (
        "name",
        "property",
        "pattern",
    ):
        name_node = node.child_by_field_name(
            field_name,
        )

        if name_node is not None:
            return name_node

    return None


def _get_value_node(
    node: Node,
) -> Node | None:
    """Return the initializer/default-value node."""

    for field_name in (
        "value",
        "right",
    ):
        value_node = node.child_by_field_name(
            field_name,
        )

        if value_node is not None:
            return value_node

    return None


def _has_token(
    node: Node,
    token: str,
    context: BuildContext,
) -> bool:
    """Return whether a node has a direct token or modifier."""

    for child in node.children:
        if child.type == token:
            return True

        child_text = _get_node_text(
            context,
            child,
        )

        if child_text == token:
            return True

    return False


def _apply_symbol_modifiers(
    builder: UASTNodeBuilder,
    node: Node,
    context: BuildContext,
) -> None:
    """Apply visibility and TypeScript symbol modifiers."""

    applied_modifiers: set[str] = set()

    for child in node.children:
        child_text = _get_node_text(
            context,
            child,
        )

        candidates = {
            child.type,
        }

        if child_text is not None:
            candidates.add(
                child_text,
            )

        visibility = next(
            (
                candidate
                for candidate in candidates
                if candidate in _VISIBILITY_MODIFIERS
            ),
            None,
        )

        if visibility is not None:
            builder.set(
                "visibility",
                visibility,
            )

        for modifier in sorted(
            candidates & _SYMBOL_MODIFIERS,
        ):
            if modifier in applied_modifiers:
                continue

            builder.append(
                "modifiers",
                modifier,
            )
            applied_modifiers.add(
                modifier,
            )


def _split_top_level_commas(
    value: str,
) -> list[str]:
    """Split comma-separated types without splitting generic arguments."""

    results: list[str] = []
    start = 0
    depth = 0

    opening_characters = {
        "<",
        "(",
        "[",
        "{",
    }
    closing_characters = {
        ">",
        ")",
        "]",
        "}",
    }

    for index, character in enumerate(value):
        if character in opening_characters:
            depth += 1
        elif character in closing_characters:
            depth = max(
                0,
                depth - 1,
            )
        elif character == "," and depth == 0:
            item = value[start:index].strip()

            if item:
                results.append(
                    item,
                )

            start = index + 1

    final_item = value[start:].strip()

    if final_item:
        results.append(
            final_item,
        )

    return results


def _extract_heritage_types(
    heritage_text: str,
) -> list[str]:
    """Extract extends/implements type expressions."""

    normalized = " ".join(
        heritage_text.split(),
    )

    keyword_matches = list(
        re.finditer(
            r"\b(?:extends|implements)\b",
            normalized,
        ),
    )

    base_types: list[str] = []

    for index, match in enumerate(keyword_matches):
        segment_start = match.end()

        if index + 1 < len(keyword_matches):
            segment_end = keyword_matches[index + 1].start()
        else:
            segment_end = len(normalized)

        segment = normalized[segment_start:segment_end].strip()

        base_types.extend(
            _split_top_level_commas(
                segment,
            ),
        )

    return base_types


def _apply_base_types(
    builder: UASTNodeBuilder,
    node: Node,
    context: BuildContext,
) -> None:
    """Apply class and interface heritage metadata."""

    for child in node.named_children:
        if child.type not in {
            "class_heritage",
            "extends_type_clause",
        }:
            continue

        heritage_text = _get_node_text(
            context,
            child,
        )

        if heritage_text is None:
            continue

        for base_type in _extract_heritage_types(
            heritage_text,
        ):
            builder.append(
                "base_types",
                base_type,
            )


def _get_function_node(
    node: Node,
) -> Node:
    """Return the actual function node behind a declaration wrapper."""

    if node.type in {
        "variable_declarator",
        "public_field_definition",
    }:
        value_node = _get_value_node(
            node,
        )

        if value_node is not None:
            return value_node

    return node


def _apply_function_metadata(
    builder: UASTNodeBuilder,
    node: Node,
    context: BuildContext,
) -> None:
    """Apply TypeScript function flags, modifiers and return type."""

    function_node = _get_function_node(
        node,
    )

    return_type_node = function_node.child_by_field_name(
        "return_type",
    )

    return_type_text = _get_node_text(
        context,
        return_type_node,
    )

    if return_type_text is not None:
        builder.set(
            "return_type",
            _strip_type_annotation(
                return_type_text,
            ),
        )

    _apply_symbol_modifiers(
        builder,
        node,
        context,
    )

    if function_node is not node:
        _apply_symbol_modifiers(
            builder,
            function_node,
            context,
        )

    if _has_token(
        function_node,
        "async",
        context,
    ):
        builder.set(
            "is_async",
            True,
        )
        builder.append(
            "modifiers",
            "async",
        )

    if _has_token(
        node,
        "static",
        context,
    ):
        builder.set(
            "is_static",
            True,
        )

    if "generator" in function_node.type or _has_token(
        function_node,
        "*",
        context,
    ):
        builder.set(
            "is_generator",
            True,
        )


class TypeScriptTypeDefinitionCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build classes, interfaces, aliases and enums."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns=[
                "definition.class",
                "definition.interface",
                "definition.type_alias",
                "definition.enum",
            ],
        )

    def create_builder(
        self,
        capture_name: str,
        ts_child: Node,
        parent_builder: UASTNodeBuilder,
        context: BuildContext,
    ) -> UASTNodeBuilder:
        """Build a TypeDefinitionNode for a TypeScript type declaration."""

        builder = UASTNodeBuilder.from_ts_node(
            ts_child,
            "definition.class",
        )
        builder.set_parent_id(
            parent_builder.id,
        )

        name_node = _get_name_node(
            ts_child,
        )

        name_text = _get_node_text(
            context,
            name_node,
        )

        if name_text is not None:
            builder.set_name(
                name_text,
            )

        kind_by_capture = {
            "definition.class": "class",
            "definition.interface": "interface",
            "definition.type_alias": "type_alias",
            "definition.enum": "enum",
        }

        builder.set(
            "kind",
            kind_by_capture[capture_name],
        )

        JavaScriptDefinitionCaptureHandler._apply_pending_docstring(
            builder,
            context,
        )

        _apply_symbol_modifiers(
            builder,
            ts_child,
            context,
        )

        if capture_name in {
            "definition.class",
            "definition.interface",
        }:
            _apply_base_types(
                builder,
                ts_child,
                context,
            )

        if capture_name == "definition.class" and _has_token(
            ts_child,
            "abstract",
            context,
        ):
            builder.set(
                "is_abstract",
                True,
            )

        if capture_name == "definition.type_alias":
            self._apply_alias_target(
                builder,
                ts_child,
                context,
            )

        if capture_name == "definition.enum":
            self._apply_enum_values(
                builder,
                ts_child,
                context,
            )

        return builder

    @staticmethod
    def _apply_alias_target(
        builder: UASTNodeBuilder,
        node: Node,
        context: BuildContext,
    ) -> None:
        """Store the right-hand side of a type alias."""

        target_node = node.child_by_field_name(
            "value",
        )

        if target_node is None:
            target_node = node.child_by_field_name(
                "type",
            )

        target_text = _get_node_text(
            context,
            target_node,
        )

        if target_text is not None:
            builder.set_metadata(
                "aliased_type",
                target_text,
            )

    @staticmethod
    def _apply_enum_values(
        builder: UASTNodeBuilder,
        node: Node,
        context: BuildContext,
    ) -> None:
        """Store enum member names."""

        body_node = node.child_by_field_name(
            "body",
        )

        if body_node is None:
            body_node = next(
                (child for child in node.named_children if child.type == "enum_body"),
                None,
            )

        if body_node is None:
            return

        for member in body_node.named_children:
            if member.type == "comment":
                continue

            name_node = member.child_by_field_name(
                "name",
            )

            if name_node is None:
                if member.type in {
                    "identifier",
                    "property_identifier",
                    "string",
                    "number",
                }:
                    name_node = member
                else:
                    name_node = next(
                        iter(member.named_children),
                        None,
                    )

            member_name = _get_node_text(
                context,
                name_node,
            )

            if member_name is not None:
                builder.append(
                    "enum_values",
                    member_name,
                )


class TypeScriptFunctionCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build TypeScript functions, methods and constructors."""

    def __init__(self) -> None:
        super().__init__(
            capture_patterns=[
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
        """Build a function-like UAST node."""

        builder = UASTNodeBuilder.from_ts_node(
            ts_child,
            capture_name,
        )
        builder.set_parent_id(
            parent_builder.id,
        )

        name_node = _get_name_node(
            ts_child,
        )

        name_text = _get_node_text(
            context,
            name_node,
        )

        if name_text is not None:
            builder.set_name(
                name_text,
            )

        JavaScriptDefinitionCaptureHandler._apply_pending_docstring(
            builder,
            context,
        )

        _apply_function_metadata(
            builder,
            ts_child,
            context,
        )

        return builder


class TypeScriptParameterCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Build required, optional, default and rest parameters."""

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
        """Build a typed parameter node."""

        builder = UASTNodeBuilder.from_ts_node(
            ts_child,
            capture_name,
        )
        builder.set_parent_id(
            parent_builder.id,
        )

        pattern_node = _get_name_node(
            ts_child,
        )

        if pattern_node is None:
            pattern_node = next(
                (
                    child
                    for child in ts_child.named_children
                    if child.type != "type_annotation"
                ),
                None,
            )

        pattern_text = _get_node_text(
            context,
            pattern_node,
        )

        if pattern_text is not None:
            if pattern_node is not None and pattern_node.type == "rest_pattern":
                pattern_text = pattern_text.removeprefix(
                    "...",
                )

            builder.set_name(
                pattern_text,
            )

        type_text = _get_type_text(
            ts_child,
            context,
        )

        if type_text is not None:
            builder.set(
                "data_type",
                type_text,
            )

        value_node = _get_value_node(
            ts_child,
        )

        value_text = _get_node_text(
            context,
            value_node,
        )

        if value_text is not None:
            builder.set(
                "initial_value",
                value_text,
            )

        if ts_child.type == "optional_parameter" or _has_token(
            ts_child,
            "?",
            context,
        ):
            builder.set_metadata(
                "optional",
                True,
            )
            builder.append(
                "modifiers",
                "optional",
            )

        if pattern_node is not None and pattern_node.type == "rest_pattern":
            builder.set_metadata(
                "rest",
                True,
            )
            builder.append(
                "modifiers",
                "rest",
            )

        _apply_symbol_modifiers(
            builder,
            ts_child,
            context,
        )

        return builder


class TypeScriptVariableCaptureHandler(
    BaseNodeCaptureHandler,
):
    """Classify typed variables, constants, fields and arrow functions."""

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
        """Build a variable-like or function-valued declaration."""

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

        name_node = _get_name_node(
            ts_child,
        )

        name_text = _get_node_text(
            context,
            name_node,
        )

        if name_text is not None:
            builder.set_name(
                name_text,
            )

        JavaScriptDefinitionCaptureHandler._apply_pending_docstring(
            builder,
            context,
        )

        type_text = _get_type_text(
            ts_child,
            context,
        )

        if type_text is not None:
            builder.set(
                "data_type",
                type_text,
            )

        value_node = _get_value_node(
            ts_child,
        )

        if effective_capture_name in {
            "definition.function",
            "definition.method",
        }:
            _apply_function_metadata(
                builder,
                ts_child,
                context,
            )
        else:
            value_text = _get_node_text(
                context,
                value_node,
            )

            if value_text is not None:
                builder.set(
                    "initial_value",
                    value_text,
                )

            _apply_symbol_modifiers(
                builder,
                ts_child,
                context,
            )

        return builder

    @classmethod
    def _resolve_definition_capture(
        cls,
        node: Node,
        original_capture_name: str,
    ) -> str:
        """Resolve the semantic kind of a TS variable or field."""

        value_node = _get_value_node(
            node,
        )

        if value_node is not None and value_node.type in _FUNCTION_VALUE_NODE_TYPES:
            if node.type == "public_field_definition":
                return "definition.method"

            return "definition.function"

        if node.type == "public_field_definition":
            return "definition.field"

        if cls._is_const_declaration(
            node,
        ):
            return "definition.constant"

        return original_capture_name

    @staticmethod
    def _is_const_declaration(
        node: Node,
    ) -> bool:
        """Return whether a variable belongs to a const declaration."""

        parent = node.parent

        if parent is None or parent.type != "lexical_declaration":
            return False

        return any(child.type == "const" for child in parent.children)


class TypeScriptAdapter(LanguageAdapter):
    """Convert TypeScript-family captures into UAST nodes."""

    def __init__(
        self,
        *,
        query: Query,
    ) -> None:
        super().__init__(
            language_name="typescript",
            query=query,
            handlers=[
                JavaScriptMetadataCaptureHandler(),
                JavaScriptDependencyCaptureHandler(),
                TypeScriptParameterCaptureHandler(),
                TypeScriptVariableCaptureHandler(),
                TypeScriptTypeDefinitionCaptureHandler(),
                TypeScriptFunctionCaptureHandler(),
                JavaScriptCallCaptureHandler(),
                JavaScriptAttributeCaptureHandler(),
            ],
            capture_priorities={
                "definition.constructor": 1,
                "dependency.import": 2,
                "definition.interface": 3,
                "definition.type_alias": 4,
                "definition.enum": 5,
                "definition.class": 6,
                "definition.method": 7,
                "definition.function": 8,
                "definition.constant": 9,
                "definition.field": 10,
                "definition.variable": 11,
                "definition.parameter": 12,
                "reference.call": 20,
                "reference.attribute": 30,
            },
        )


@lru_cache
def get_typescript_adapter() -> LanguageAdapter:
    """Return the adapter compiled for plain TypeScript."""

    return TypeScriptAdapter(
        query=get_typescript_query(),
    )


@lru_cache
def get_tsx_adapter() -> LanguageAdapter:
    """Return the adapter compiled for TSX."""

    return TypeScriptAdapter(
        query=get_tsx_query(),
    )
