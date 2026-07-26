"""Tests for repository-level chunking orchestration."""

import pytest

from app.chunking import (
    ChunkingOptions,
    RepositoryChunkingError,
    RepositoryChunkingService,
)
from app.domain.source_file import (
    compute_source_content_hash,
)
from app.parser import (
    ParserService,
)
from app.parser.repository_contracts import (
    ParsedSourceFile,
    RepositoryParseBatch,
    SourceFileChange,
)


def make_parsed_file(
    source: str,
    *,
    relative_path: str,
    change: SourceFileChange,
) -> ParsedSourceFile:
    """Create one valid ParsedSourceFile fixture."""

    source_bytes = source.encode(
        "utf-8",
    )

    parse_result = ParserService().parse_bytes(
        source_bytes,
        file_path=relative_path,
    )

    return ParsedSourceFile(
        relative_path=relative_path,
        content_hash=compute_source_content_hash(
            source_bytes,
        ),
        change=change,
        parse_result=parse_result,
    )


def test_repository_service_chunks_added_and_modified_files() -> None:
    added_file = make_parsed_file(
        "def alpha() -> int:\n    return 1\n",
        relative_path="src/alpha.py",
        change=SourceFileChange.ADDED,
    )

    modified_file = make_parsed_file(
        "export const beta = (): number => 2;\n",
        relative_path="src/beta.ts",
        change=SourceFileChange.MODIFIED,
    )

    parse_batch = RepositoryParseBatch(
        parsed_files=(
            modified_file,
            added_file,
        ),
        unchanged_paths=(),
        deleted_paths=(),
        current_files=(),
    )

    result = RepositoryChunkingService().chunk_parse_batch(
        parse_batch,
        options=ChunkingOptions(
            max_size=24,
        ),
    )

    assert list(result.changed_paths) == [
        "src/alpha.py",
        "src/beta.ts",
    ]

    assert result.chunk_count > 0
    assert result.has_changes is True

    assert all(
        file_result.chunking_result.coverage.is_exact
        for file_result in result.chunked_files
    )

    assert all(
        file_result.chunking_result.over_limit_count == 0
        for file_result in result.chunked_files
    )


def test_repository_service_propagates_unchanged_and_deleted_paths() -> None:
    parse_batch = RepositoryParseBatch(
        parsed_files=(),
        unchanged_paths=("src/stable.py",),
        deleted_paths=("src/deleted.ts",),
        current_files=(),
    )

    result = RepositoryChunkingService().chunk_parse_batch(
        parse_batch,
    )

    assert result.chunked_files == ()
    assert result.unchanged_paths == ("src/stable.py",)
    assert result.deleted_paths == ("src/deleted.ts",)
    assert result.has_changes is True


def test_unchanged_only_batch_has_no_index_changes() -> None:
    parse_batch = RepositoryParseBatch(
        parsed_files=(),
        unchanged_paths=("src/stable.py",),
        deleted_paths=(),
        current_files=(),
    )

    result = RepositoryChunkingService().chunk_parse_batch(
        parse_batch,
    )

    assert result.chunk_count == 0
    assert result.has_changes is False


def test_partial_parse_result_is_chunked() -> None:
    parsed_file = make_parsed_file(
        ("def valid() -> int:\n    return 1\n\ndef broken(\n"),
        relative_path="src/broken.py",
        change=SourceFileChange.MODIFIED,
    )

    parse_batch = RepositoryParseBatch(
        parsed_files=(parsed_file,),
        unchanged_paths=(),
        deleted_paths=(),
        current_files=(),
    )

    result = RepositoryChunkingService().chunk_parse_batch(
        parse_batch,
        options=ChunkingOptions(
            max_size=20,
        ),
    )

    assert (
        len(
            result.chunked_files,
        )
        == 1
    )

    assert result.chunked_files[0].chunking_result.coverage.is_exact is True


def test_path_mismatch_is_rejected() -> None:
    source_bytes = b"value = 1\n"

    parse_result = ParserService().parse_bytes(
        source_bytes,
        file_path="src/actual.py",
    )

    parsed_file = ParsedSourceFile(
        "src/expected.py",
        content_hash=compute_source_content_hash(
            source_bytes,
        ),
        change=SourceFileChange.ADDED,
        parse_result=parse_result,
    )

    parse_batch = RepositoryParseBatch(
        parsed_files=(parsed_file,),
        unchanged_paths=(),
        deleted_paths=(),
        current_files=(),
    )

    with pytest.raises(
        RepositoryChunkingError,
        match="does not match",
    ):
        RepositoryChunkingService().chunk_parse_batch(
            parse_batch,
        )


def test_hash_mismatch_is_rejected() -> None:
    source_bytes = b"value = 1\n"

    parse_result = ParserService().parse_bytes(
        source_bytes,
        file_path="src/value.py",
    )

    parsed_file = ParsedSourceFile(
        "src/value.py",
        content_hash="0" * 64,
        change=SourceFileChange.ADDED,
        parse_result=parse_result,
    )

    parse_batch = RepositoryParseBatch(
        parsed_files=(parsed_file,),
        unchanged_paths=(),
        deleted_paths=(),
        current_files=(),
    )

    with pytest.raises(
        RepositoryChunkingError,
        match="content hash",
    ):
        RepositoryChunkingService().chunk_parse_batch(
            parse_batch,
        )
