"""Integration tests for incremental repository parsing."""

from hashlib import sha256
from pathlib import Path, PurePosixPath

import pytest

from app.domain.source_file import (
    compute_source_content_hash,
)
from app.parser import (
    ParseStatus,
    RepositoryParserService,
    SourceFileChange,
    StaleScannedSourceFileError,
)
from app.repository_manager.scanner import (
    RepositoryScanner,
)


def write_source(
    repository_root: Path,
    relative_path: str,
    source: str,
) -> Path:
    """Write a UTF-8 source file inside a test repository."""

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

    absolute_path.write_text(
        source,
        encoding="utf-8",
    )

    return absolute_path


@pytest.fixture
def scanner() -> RepositoryScanner:
    """Return a repository scanner."""

    return RepositoryScanner()


@pytest.fixture
def repository_parser() -> RepositoryParserService:
    """Return an incremental repository parser."""

    return RepositoryParserService()


def test_compute_source_content_hash_uses_sha256() -> None:
    source_bytes = ('const message = "Tổng";\n').encode(
        "utf-8",
    )

    assert (
        compute_source_content_hash(
            source_bytes,
        )
        == sha256(
            source_bytes,
        ).hexdigest()
    )


def test_added_files_are_parsed_for_supported_languages(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    write_source(
        tmp_path,
        "src/service.py",
        "def execute():\n    return 1\n",
    )
    write_source(
        tmp_path,
        "src/app.jsx",
        "const App = () => <main />;\n",
    )
    write_source(
        tmp_path,
        "src/service.ts",
        "const value: number = 1;\n",
    )
    write_source(
        tmp_path,
        "src/Card.tsx",
        "const Card = (): JSX.Element => <article />;\n",
    )

    scan_result = scanner.scan(
        tmp_path,
    )

    batch = repository_parser.parse_scan_result(
        scan_result,
    )

    assert batch.has_changes is True
    assert batch.unchanged_paths == ()
    assert batch.deleted_paths == ()
    assert len(batch.parsed_files) == 4
    assert len(batch.current_files) == 4

    by_path = {file.relative_path: file for file in batch.parsed_files}

    assert by_path["src/service.py"].change is SourceFileChange.ADDED
    assert by_path["src/service.py"].parse_result.language == "python"

    assert by_path["src/app.jsx"].parse_result.language == "javascript"

    assert by_path["src/service.ts"].parse_result.parser_name == "typescript"

    assert by_path["src/Card.tsx"].parse_result.language == "typescript"
    assert by_path["src/Card.tsx"].parse_result.parser_name == "tsx"

    assert all(
        file.parse_result.status is ParseStatus.SUCCESS for file in batch.parsed_files
    )


def test_unchanged_files_are_not_parsed_again(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    write_source(
        tmp_path,
        "src/service.py",
        "value = 1\n",
    )
    write_source(
        tmp_path,
        "src/service.ts",
        "const value: number = 1;\n",
    )

    first_scan = scanner.scan(
        tmp_path,
    )
    first_batch = repository_parser.parse_scan_result(
        first_scan,
    )

    second_scan = scanner.scan(
        tmp_path,
    )
    second_batch = repository_parser.parse_scan_result(
        second_scan,
        previous_hashes=(first_batch.current_hashes),
    )

    assert second_batch.parsed_files == ()
    assert second_batch.deleted_paths == ()
    assert second_batch.unchanged_paths == (
        "src/service.py",
        "src/service.ts",
    )
    assert second_batch.has_changes is False
    assert second_batch.current_hashes == first_batch.current_hashes


def test_modified_and_deleted_files_are_detected(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    python_file = write_source(
        tmp_path,
        "src/service.py",
        "value = 1\n",
    )
    typescript_file = write_source(
        tmp_path,
        "src/service.ts",
        "const value: number = 1;\n",
    )

    first_scan = scanner.scan(
        tmp_path,
    )
    first_batch = repository_parser.parse_scan_result(
        first_scan,
    )

    python_file.write_text(
        "value = 2\n",
        encoding="utf-8",
    )
    typescript_file.unlink()

    second_scan = scanner.scan(
        tmp_path,
    )
    second_batch = repository_parser.parse_scan_result(
        second_scan,
        previous_hashes=(first_batch.current_hashes),
    )

    assert (
        len(
            second_batch.parsed_files,
        )
        == 1
    )

    parsed_file = second_batch.parsed_files[0]

    assert parsed_file.relative_path == "src/service.py"
    assert parsed_file.change is SourceFileChange.MODIFIED

    assert second_batch.deleted_paths == ("src/service.ts",)
    assert second_batch.unchanged_paths == ()
    assert second_batch.has_changes is True


def test_partial_parse_is_retained_in_batch(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    write_source(
        tmp_path,
        "src/broken.py",
        "def broken()\n    return 1\n",
    )

    scan_result = scanner.scan(
        tmp_path,
    )

    batch = repository_parser.parse_scan_result(
        scan_result,
    )

    assert len(batch.parsed_files) == 1

    parse_result = batch.parsed_files[0].parse_result

    assert parse_result.status is ParseStatus.PARTIAL
    assert parse_result.has_errors is True
    assert parse_result.diagnostics


def test_file_changed_after_scan_is_rejected(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    source_file = write_source(
        tmp_path,
        "src/service.py",
        "value = 1\n",
    )

    scan_result = scanner.scan(
        tmp_path,
    )

    source_file.write_text(
        "value = 999\n",
        encoding="utf-8",
    )

    with pytest.raises(
        StaleScannedSourceFileError,
    ):
        repository_parser.parse_scan_result(
            scan_result,
        )


def test_duplicate_scanned_paths_are_rejected(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    write_source(
        tmp_path,
        "src/service.py",
        "value = 1\n",
    )

    scan_result = scanner.scan(
        tmp_path,
    )

    scanned_file = scan_result.files[0]

    with pytest.raises(
        ValueError,
        match="Duplicate scanned source path",
    ):
        repository_parser.parse_scanned_files(
            (
                scanned_file,
                scanned_file,
            ),
        )


def test_previous_windows_paths_are_normalized(
    tmp_path: Path,
    scanner: RepositoryScanner,
    repository_parser: RepositoryParserService,
) -> None:
    write_source(
        tmp_path,
        "src/service.py",
        "value = 1\n",
    )

    scan_result = scanner.scan(
        tmp_path,
    )

    scanned_file = scan_result.files[0]

    batch = repository_parser.parse_scan_result(
        scan_result,
        previous_hashes={
            "src\\service.py": (scanned_file.content_hash),
        },
    )

    assert batch.parsed_files == ()
    assert batch.unchanged_paths == ("src/service.py",)
    assert batch.deleted_paths == ()
