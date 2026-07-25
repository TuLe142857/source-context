"""Public output contracts for source parsing."""

from dataclasses import dataclass
from enum import StrEnum

from .uast import UASTNode


class ParseStatus(StrEnum):
    """Overall state of a parse operation."""

    SUCCESS = "success"
    PARTIAL = "partial"


class ParseDiagnosticSeverity(StrEnum):
    """Severity assigned to a parser diagnostic."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ParseDiagnosticKind(StrEnum):
    """Machine-readable parser diagnostic categories."""

    SYNTAX_ERROR = "syntax_error"
    MISSING_NODE = "missing_node"


@dataclass(frozen=True, slots=True)
class SourcePoint:
    """Zero-based source position compatible with Tree-sitter."""

    row: int
    column: int

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serializable representation."""

        return {
            "row": self.row,
            "column": self.column,
        }


@dataclass(frozen=True, slots=True)
class SourceRange:
    """Byte and row-column range of a source construct."""

    start_byte: int
    end_byte: int
    start_point: SourcePoint
    end_point: SourcePoint

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "start_point": self.start_point.to_dict(),
            "end_point": self.end_point.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ParseDiagnostic:
    """One syntax problem reported by Tree-sitter."""

    kind: ParseDiagnosticKind
    severity: ParseDiagnosticSeverity
    message: str
    node_type: str
    source_range: SourceRange
    excerpt: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "message": self.message,
            "node_type": self.node_type,
            "source_range": self.source_range.to_dict(),
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Normalized result returned by ParserService."""

    file_path: str
    language: str
    parser_name: str
    status: ParseStatus
    source_size_bytes: int
    diagnostics: tuple[ParseDiagnostic, ...]
    uast_root: UASTNode

    @property
    def has_errors(self) -> bool:
        """Return whether at least one error diagnostic exists."""

        return any(
            diagnostic.severity is ParseDiagnosticSeverity.ERROR
            for diagnostic in self.diagnostics
        )

    @property
    def is_clean(self) -> bool:
        """Return whether parsing completed without diagnostics."""

        return self.status is ParseStatus.SUCCESS

    def to_dict(self) -> dict[str, object]:
        """Return the serializable part of the parse result.

        The UAST object is intentionally excluded because UAST
        serialization is a separate contract and may contain source bytes.
        """

        return {
            "file_path": self.file_path,
            "language": self.language,
            "parser_name": self.parser_name,
            "status": self.status.value,
            "source_size_bytes": self.source_size_bytes,
            "has_errors": self.has_errors,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
