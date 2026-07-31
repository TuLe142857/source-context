"""Integration tests for production structural chunking."""

from collections.abc import Sequence

from app.chunking import SourceChunk
from app.parser import ParseResult

from app.chunking import (
    ChunkingOptions,
    ChunkingService,
    ChunkSizeUnit,
)
from app.parser import (
    ParseStatus,
    ParserService,
)


def parse_source(
    source: str,
    *,
    file_path: str,
) -> ParseResult:
    """Parse source using the production ParserService."""

    return ParserService().parse_text(
        source,
        file_path=file_path,
    )


def rebuild_source_bytes(
    chunks: Sequence[SourceChunk],
    source_bytes: bytes,
) -> bytes:
    """Rebuild source bytes using generated chunk ranges."""

    return b"".join(source_bytes[chunk.start_byte : chunk.end_byte] for chunk in chunks)


def test_structural_functions_are_chunked_exactly() -> None:
    source = (
        "def first(value: int) -> int:\n"
        "    return value + 1\n"
        "\n"
        "\n"
        "def second(value: int) -> int:\n"
        "    return value * 2\n"
    )

    parse_result = parse_source(
        source,
        file_path="src/service.py",
    )

    result = ChunkingService().chunk_parse_result(
        parse_result,
        options=ChunkingOptions(
            max_size=65,
        ),
    )

    source_bytes = source.encode(
        "utf-8",
    )

    assert result.coverage.is_exact is True
    assert result.over_limit_count == 0
    assert (
        rebuild_source_bytes(
            result.chunks,
            source_bytes,
        )
        == source_bytes
    )

    symbol_names = {
        chunk.symbol_name for chunk in result.chunks if chunk.symbol_name is not None
    }

    assert {
        "first",
        "second",
    }.issubset(
        symbol_names,
    )


def test_oversized_leaf_uses_strict_fallback() -> None:
    source = 'def build_message() -> str:\n    return "' + ("x" * 180) + '"\n'

    parse_result = parse_source(
        source,
        file_path="src/message.py",
    )

    options = ChunkingOptions(
        max_size=32,
    )

    result = ChunkingService().chunk_parse_result(
        parse_result,
        options=options,
    )

    source_bytes = source.encode(
        "utf-8",
    )

    assert result.chunk_count > 1
    assert result.coverage.is_exact is True
    assert result.over_limit_count == 0

    assert all(chunk.size <= options.max_size for chunk in result.chunks)

    assert (
        rebuild_source_bytes(
            result.chunks,
            source_bytes,
        )
        == source_bytes
    )


def test_word_unit_respects_word_limit() -> None:
    source = 'const message = "one two three four five six seven eight nine ten";\n'

    parse_result = parse_source(
        source,
        file_path="src/message.js",
    )

    options = ChunkingOptions(
        max_size=3,
        size_unit=ChunkSizeUnit.WORD,
    )

    result = ChunkingService().chunk_parse_result(
        parse_result,
        options=options,
    )

    assert result.coverage.is_exact is True
    assert result.over_limit_count == 0

    assert all(chunk.size <= 3 for chunk in result.chunks)


def test_tsx_keeps_typescript_language_and_tsx_parser() -> None:
    source = (
        "type Props = {\n"
        "  title: string;\n"
        "};\n"
        "\n"
        "export const Card = "
        "({ title }: Props): JSX.Element => (\n"
        "  <article>{title}</article>\n"
        ");\n"
    )

    parse_result = parse_source(
        source,
        file_path="src/Card.tsx",
    )

    result = ChunkingService().chunk_parse_result(
        parse_result,
        options=ChunkingOptions(
            max_size=64,
        ),
    )

    assert result.language == "typescript"
    assert result.parser_name == "tsx"
    assert result.coverage.is_exact is True
    assert result.over_limit_count == 0


def test_unicode_and_crlf_preserve_exact_bytes() -> None:
    source = (
        "def tính_tổng(a: int, b: int) -> int:\r\n"
        "    thông_báo = 'Tổng giá trị'\r\n"
        "    return a + b\r\n"
    )

    parse_result = parse_source(
        source,
        file_path="src/calculator.py",
    )

    result = ChunkingService().chunk_parse_result(
        parse_result,
        options=ChunkingOptions(
            max_size=28,
        ),
    )

    source_bytes = source.encode(
        "utf-8",
    )

    assert result.coverage.is_exact is True
    assert result.over_limit_count == 0

    assert (
        rebuild_source_bytes(
            result.chunks,
            source_bytes,
        )
        == source_bytes
    )


def test_partial_parse_result_can_still_be_chunked() -> None:
    source = "def valid() -> int:\n    return 1\n\ndef broken(\n"

    parse_result = parse_source(
        source,
        file_path="src/broken.py",
    )

    assert parse_result.status is ParseStatus.PARTIAL

    result = ChunkingService().chunk_parse_result(
        parse_result,
        options=ChunkingOptions(
            max_size=24,
        ),
    )

    assert result.coverage.is_exact is True
    assert result.over_limit_count == 0
    assert result.chunks


def test_empty_source_returns_empty_exact_result() -> None:
    parse_result = parse_source(
        "",
        file_path="src/empty.py",
    )

    result = ChunkingService().chunk_parse_result(
        parse_result,
    )

    assert result.chunk_count == 0
    assert result.chunks == ()
    assert result.coverage.is_exact is True
    assert result.coverage.total_bytes == 0


def test_disabling_merge_preserves_more_structural_units() -> None:
    source = "value_a = 1\nvalue_b = 2\nvalue_c = 3\n"

    parse_result = parse_source(
        source,
        file_path="src/values.py",
    )

    service = ChunkingService()

    merged = service.chunk_parse_result(
        parse_result,
        options=ChunkingOptions(
            max_size=25,
            merge_adjacent=True,
        ),
    )

    unmerged = service.chunk_parse_result(
        parse_result,
        options=ChunkingOptions(
            max_size=25,
            merge_adjacent=False,
        ),
    )

    assert merged.coverage.is_exact is True
    assert unmerged.coverage.is_exact is True

    assert unmerged.chunk_count >= merged.chunk_count
