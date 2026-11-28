"""Tree-sitter syntax diagnostic extraction."""

from tree_sitter import Node

from .contracts import (
    ParseDiagnostic,
    ParseDiagnosticKind,
    ParseDiagnosticSeverity,
    SourcePoint,
    SourceRange,
)


_MAX_EXCERPT_BYTES = 120
_MISSING_CONTEXT_BYTES = 40


def _make_source_range(
    node: Node,
) -> SourceRange:
    """Convert a Tree-sitter node range to the public contract."""

    return SourceRange(
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_point=SourcePoint(
            row=node.start_point.row,
            column=node.start_point.column,
        ),
        end_point=SourcePoint(
            row=node.end_point.row,
            column=node.end_point.column,
        ),
    )


def _extract_excerpt(
    source_bytes: bytes,
    *,
    start_byte: int,
    end_byte: int,
) -> str | None:
    """Extract a compact UTF-8-safe diagnostic excerpt."""

    source_length = len(source_bytes)

    start = max(
        0,
        min(start_byte, source_length),
    )
    end = max(
        start,
        min(end_byte, source_length),
    )

    if start == end:
        excerpt_start = max(
            0,
            start - _MISSING_CONTEXT_BYTES,
        )
        excerpt_end = min(
            source_length,
            end + _MISSING_CONTEXT_BYTES,
        )
    else:
        excerpt_start = start
        excerpt_end = min(
            end,
            start + _MAX_EXCERPT_BYTES,
        )

    if excerpt_start == excerpt_end:
        return None

    excerpt = source_bytes[excerpt_start:excerpt_end].decode(
        "utf-8",
        errors="replace",
    )

    return excerpt.replace(
        "\r",
        "\\r",
    ).replace(
        "\n",
        "\\n",
    )


def _make_diagnostic(
    node: Node,
    source_bytes: bytes,
) -> ParseDiagnostic | None:
    """Create a diagnostic for an ERROR or MISSING node."""

    if node.is_missing:
        kind = ParseDiagnosticKind.MISSING_NODE
        message = f"Missing syntax element: {node.type}."
    elif node.is_error:
        kind = ParseDiagnosticKind.SYNTAX_ERROR
        message = "Unexpected or invalid syntax."
    else:
        return None

    return ParseDiagnostic(
        kind=kind,
        severity=ParseDiagnosticSeverity.ERROR,
        message=message,
        node_type=node.type,
        source_range=_make_source_range(node),
        excerpt=_extract_excerpt(
            source_bytes,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )


def collect_parse_diagnostics(
    root_node: Node,
    source_bytes: bytes,
) -> tuple[ParseDiagnostic, ...]:
    """Collect syntax diagnostics in deterministic source order."""

    if not root_node.has_error:
        return ()

    diagnostics: list[ParseDiagnostic] = []
    stack = [root_node]

    while stack:
        node = stack.pop()

        diagnostic = _make_diagnostic(
            node,
            source_bytes,
        )

        if diagnostic is not None:
            diagnostics.append(
                diagnostic,
            )

        # Reverse push preserves left-to-right traversal.
        stack.extend(
            reversed(node.children),
        )

    if not diagnostics:
        diagnostics.append(
            ParseDiagnostic(
                kind=ParseDiagnosticKind.SYNTAX_ERROR,
                severity=ParseDiagnosticSeverity.ERROR,
                message=("The syntax tree contains an unclassified parse error."),
                node_type=root_node.type,
                source_range=_make_source_range(
                    root_node,
                ),
                excerpt=_extract_excerpt(
                    source_bytes,
                    start_byte=root_node.start_byte,
                    end_byte=root_node.end_byte,
                ),
            ),
        )

    diagnostics.sort(
        key=lambda diagnostic: (
            diagnostic.source_range.start_byte,
            diagnostic.source_range.end_byte,
            diagnostic.kind.value,
        ),
    )

    return tuple(
        diagnostics,
    )
