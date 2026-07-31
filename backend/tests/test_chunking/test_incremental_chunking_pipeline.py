"""End-to-end tests for incremental repository parsing and chunking."""

from pathlib import Path, PurePosixPath

from app.chunking import (
    ChunkingOptions,
    RepositoryChunkingBatch,
    RepositoryChunkingService,
)
from app.parser.repository_contracts import SourceFileChange
from app.parser.repository_service import RepositoryParserService
from app.repository_manager.scanner import RepositoryScanner


def write_source(
    repository_root: Path,
    relative_path: str,
    source: str,
) -> Path:
    """Write one UTF-8 source fixture without newline translation."""

    normalized_path = PurePosixPath(
        relative_path,
    )

    absolute_path = repository_root.joinpath(
        *normalized_path.parts,
    )

    absolute_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    absolute_path.write_bytes(
        source.encode(
            "utf-8",
        ),
    )

    return absolute_path


def resolve_repository_path(
    repository_root: Path,
    relative_path: str,
) -> Path:
    """Resolve a normalized repository-relative path."""

    normalized_path = PurePosixPath(
        relative_path,
    )

    return repository_root.joinpath(
        *normalized_path.parts,
    )


def rebuild_file_from_chunks(
    repository_root: Path,
    relative_path: str,
    batch: RepositoryChunkingBatch,
) -> bytes:
    """Rebuild one changed file from generated chunk ranges."""

    chunked_file = next(
        item for item in batch.chunked_files if item.relative_path == relative_path
    )

    source_path = resolve_repository_path(
        repository_root,
        relative_path,
    )
    source_bytes = source_path.read_bytes()

    return b"".join(
        source_bytes[chunk.start_byte : chunk.end_byte]
        for chunk in (chunked_file.chunking_result.chunks)
    )


def assert_batch_has_exact_coverage(
    repository_root: Path,
    batch: RepositoryChunkingBatch,
) -> None:
    """Assert every changed file has exact reconstructable chunks."""

    for chunked_file in batch.chunked_files:
        result = chunked_file.chunking_result

        assert result.coverage.is_exact is True
        assert result.coverage.missing_bytes == 0
        assert result.coverage.overlap_bytes == 0
        assert result.over_limit_count == 0

        source_path = resolve_repository_path(
            repository_root,
            chunked_file.relative_path,
        )

        rebuilt_source = rebuild_file_from_chunks(
            repository_root,
            chunked_file.relative_path,
            batch,
        )

        assert rebuilt_source == source_path.read_bytes()


def test_incremental_repository_chunking_pipeline(
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository"

    write_source(
        repository_root,
        "src/alpha.py",
        ("def alpha(value: int) -> int:\n    return value + 1\n"),
    )

    write_source(
        repository_root,
        "src/Card.tsx",
        (
            "type Props = {\n"
            "  title: string;\n"
            "};\n"
            "\n"
            "export const Card = "
            "({ title }: Props): JSX.Element => (\n"
            "  <article>{title}</article>\n"
            ");\n"
        ),
    )

    write_source(
        repository_root,
        "src/stable.js",
        ("export function stable(value) {\n  return value;\n}\n"),
    )

    write_source(
        repository_root,
        "README.md",
        "# Unsupported documentation fixture\n",
    )

    scanner = RepositoryScanner()
    parser_service = RepositoryParserService()
    chunking_service = RepositoryChunkingService()

    options = ChunkingOptions(
        max_size=48,
    )

    # -------------------------------------------------
    # First indexing run:
    # all supported files are new.
    # -------------------------------------------------
    first_scan = scanner.scan(
        repository_root,
    )

    first_parse_batch = parser_service.parse_scan_result(
        first_scan,
    )

    first_chunk_batch = chunking_service.chunk_parse_batch(
        first_parse_batch,
        options=options,
    )

    first_changes = {
        item.relative_path: item.change for item in first_chunk_batch.chunked_files
    }

    assert first_changes == {
        "src/Card.tsx": SourceFileChange.ADDED,
        "src/alpha.py": SourceFileChange.ADDED,
        "src/stable.js": SourceFileChange.ADDED,
    }

    assert first_chunk_batch.unchanged_paths == ()
    assert first_chunk_batch.deleted_paths == ()
    assert first_chunk_batch.has_changes is True
    assert first_chunk_batch.chunk_count > 0

    assert_batch_has_exact_coverage(
        repository_root,
        first_chunk_batch,
    )

    first_hashes = first_chunk_batch.current_hashes

    assert set(first_hashes) == {
        "src/Card.tsx",
        "src/alpha.py",
        "src/stable.js",
    }

    assert "README.md" not in first_hashes

    # -------------------------------------------------
    # Second indexing run:
    # no files changed.
    # -------------------------------------------------
    second_scan = scanner.scan(
        repository_root,
    )

    second_parse_batch = parser_service.parse_scan_result(
        second_scan,
        previous_hashes=first_hashes,
    )

    assert second_parse_batch.parsed_files == ()

    second_chunk_batch = chunking_service.chunk_parse_batch(
        second_parse_batch,
        options=options,
    )

    assert second_chunk_batch.chunked_files == ()
    assert second_chunk_batch.deleted_paths == ()

    assert set(
        second_chunk_batch.unchanged_paths,
    ) == {
        "src/Card.tsx",
        "src/alpha.py",
        "src/stable.js",
    }

    assert second_chunk_batch.chunk_count == 0
    assert second_chunk_batch.has_changes is False

    assert second_chunk_batch.current_hashes == first_hashes

    # -------------------------------------------------
    # Third indexing run:
    #
    # alpha.py   -> modified
    # Card.tsx   -> deleted
    # stable.js  -> unchanged
    # service.ts -> added
    # -------------------------------------------------
    write_source(
        repository_root,
        "src/alpha.py",
        ("def alpha(value: int) -> int:\n    result = value + 2\n    return result\n"),
    )

    card_path = resolve_repository_path(
        repository_root,
        "src/Card.tsx",
    )
    card_path.unlink()

    write_source(
        repository_root,
        "src/service.ts",
        (
            "export class Service {\n"
            "  execute(value: number): number {\n"
            "    return value * 2;\n"
            "  }\n"
            "}\n"
        ),
    )

    third_scan = scanner.scan(
        repository_root,
    )

    third_parse_batch = parser_service.parse_scan_result(
        third_scan,
        previous_hashes=(second_chunk_batch.current_hashes),
    )

    third_chunk_batch = chunking_service.chunk_parse_batch(
        third_parse_batch,
        options=options,
    )

    third_changes = {
        item.relative_path: item.change for item in third_chunk_batch.chunked_files
    }

    assert third_changes == {
        "src/alpha.py": SourceFileChange.MODIFIED,
        "src/service.ts": SourceFileChange.ADDED,
    }

    assert third_chunk_batch.unchanged_paths == ("src/stable.js",)

    assert third_chunk_batch.deleted_paths == ("src/Card.tsx",)

    assert third_chunk_batch.has_changes is True

    assert set(
        third_chunk_batch.current_hashes,
    ) == {
        "src/alpha.py",
        "src/service.ts",
        "src/stable.js",
    }

    assert "src/Card.tsx" not in third_chunk_batch.current_hashes

    assert_batch_has_exact_coverage(
        repository_root,
        third_chunk_batch,
    )
