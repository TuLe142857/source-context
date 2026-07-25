"""Tests for the public ParserService contract."""

import json

import pytest

from app.parser import (
    ParseDiagnosticKind,
    ParseDiagnosticSeverity,
    ParseStatus,
    ParserService,
    UnsupportedLanguageError,
)


@pytest.fixture
def parser_service() -> ParserService:
    """Return the default parser service."""

    return ParserService()


@pytest.mark.parametrize(
    (
        "file_path",
        "source",
        "expected_language",
        "expected_parser",
    ),
    [
        (
            "src/service.py",
            "def execute() -> int:\n    return 1\n",
            "python",
            "python",
        ),
        (
            "src/component.jsx",
            "const App = () => <main>Hello</main>;\n",
            "javascript",
            "javascript",
        ),
        (
            "src/service.ts",
            "const value: number = 1;\n",
            "typescript",
            "typescript",
        ),
        (
            "src/Card.tsx",
            "const Card = (): JSX.Element => <article>Card</article>;\n",
            "typescript",
            "tsx",
        ),
    ],
)
def test_parse_clean_supported_source(
    parser_service: ParserService,
    file_path: str,
    source: str,
    expected_language: str,
    expected_parser: str,
) -> None:
    """Supported clean source should return a successful result."""

    result = parser_service.parse_text(
        source,
        file_path=file_path,
    )

    assert result.file_path == file_path
    assert result.language == expected_language
    assert result.parser_name == expected_parser
    assert result.status is ParseStatus.SUCCESS
    assert result.is_clean is True
    assert result.has_errors is False
    assert result.diagnostics == ()
    assert result.source_size_bytes == len(
        source.encode("utf-8"),
    )


def test_tsx_uses_typescript_domain_language(
    parser_service: ParserService,
) -> None:
    """TSX is a dialect, not a separate domain language."""

    result = parser_service.parse_text(
        "export const App = () => <div />;\n",
        file_path="src/App.tsx",
    )

    assert result.language == "typescript"
    assert result.parser_name == "tsx"


def test_uppercase_extension_is_supported(
    parser_service: ParserService,
) -> None:
    """Registry lookup should normalize the extension case."""

    result = parser_service.parse_text(
        "value = 1\n",
        file_path="SRC/SERVICE.PY",
    )

    assert result.file_path == "SRC/SERVICE.PY"
    assert result.language == "python"
    assert result.parser_name == "python"
    assert result.status is ParseStatus.SUCCESS


def test_malformed_source_returns_partial_result(
    parser_service: ParserService,
) -> None:
    """Malformed source should return diagnostics and partial UAST."""

    source = "def broken()\n    return 1\n"

    source_bytes = source.encode(
        "utf-8",
    )

    result = parser_service.parse_bytes(
        source_bytes,
        file_path="broken.py",
    )

    assert result.status is ParseStatus.PARTIAL
    assert result.is_clean is False
    assert result.has_errors is True
    assert result.diagnostics
    assert result.uast_root is not None

    for diagnostic in result.diagnostics:
        assert diagnostic.severity is (ParseDiagnosticSeverity.ERROR)
        assert diagnostic.kind in {
            ParseDiagnosticKind.SYNTAX_ERROR,
            ParseDiagnosticKind.MISSING_NODE,
        }

        source_range = diagnostic.source_range

        assert (
            0 <= source_range.start_byte <= source_range.end_byte <= len(source_bytes)
        )
        assert source_range.start_point.row >= 0
        assert source_range.start_point.column >= 0
        assert source_range.end_point.row >= 0
        assert source_range.end_point.column >= 0


def test_parse_result_summary_is_json_serializable(
    parser_service: ParserService,
) -> None:
    """The public summary must not expose Tree-sitter or raw bytes."""

    result = parser_service.parse_text(
        'const message: string = "Tổng";\n',
        file_path="message.ts",
    )

    payload = result.to_dict()

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
    )

    assert '"status": "success"' in serialized
    assert payload["language"] == "typescript"
    assert payload["parser_name"] == "typescript"
    assert "uast_root" not in payload
    assert "source_bytes" not in payload


def test_unicode_source_size_is_counted_in_bytes(
    parser_service: ParserService,
) -> None:
    """Source size must use UTF-8 bytes, not character count."""

    source = 'const message = "Tổng";\n'
    source_bytes = source.encode(
        "utf-8",
    )

    result = parser_service.parse_bytes(
        source_bytes,
        file_path="message.js",
    )

    assert result.source_size_bytes == len(
        source_bytes,
    )
    assert result.source_size_bytes > len(
        source,
    )


@pytest.mark.parametrize(
    "file_path",
    [
        "README.md",
        "Service.java",
        "main.go",
    ],
)
def test_unsupported_file_raises(
    parser_service: ParserService,
    file_path: str,
) -> None:
    """Unsupported files remain an explicit caller error."""

    with pytest.raises(
        UnsupportedLanguageError,
    ):
        parser_service.parse_text(
            "content",
            file_path=file_path,
        )


@pytest.mark.parametrize(
    "file_path",
    [
        "",
        "   ",
        "src/",
        "src\\",
    ],
)
def test_invalid_file_path_raises(
    parser_service: ParserService,
    file_path: str,
) -> None:
    """Parsing requires a concrete filename."""

    with pytest.raises(
        ValueError,
    ):
        parser_service.parse_text(
            "value = 1\n",
            file_path=file_path,
        )
