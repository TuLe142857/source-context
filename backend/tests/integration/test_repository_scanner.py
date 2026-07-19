"""Integration tests for repository source-file scanning."""

from pathlib import Path

from app.domain.source_file import SourceLanguage
from app.repository_manager.scanner import (
    RepositoryScanner,
    RepositoryScannerConfig,
)


def test_scanner_returns_supported_source_files(
    tmp_path: Path,
) -> None:
    """Supported files should be returned with metadata."""

    source_directory = tmp_path / "src"
    source_directory.mkdir()

    python_file = source_directory / "service.py"
    python_file.write_text(
        "def execute() -> None:\n    pass\n",
        encoding="utf-8",
    )

    (source_directory / "client.ts").write_text(
        "export const value: number = 1;\n",
        encoding="utf-8",
    )

    (source_directory / "index.js").write_text(
        "export const value = 1;\n",
        encoding="utf-8",
    )

    scanner = RepositoryScanner()
    result = scanner.scan(tmp_path)

    files_by_path = {
        source_file.relative_path.as_posix(): source_file for source_file in result.files
    }

    assert set(files_by_path) == {
        "src/client.ts",
        "src/index.js",
        "src/service.py",
    }

    assert files_by_path["src/service.py"].language is SourceLanguage.PYTHON
    assert files_by_path["src/client.ts"].language is SourceLanguage.TYPESCRIPT
    assert (
        len(
            files_by_path["src/service.py"].content_hash,
        )
        == 64
    )
    assert files_by_path["src/service.py"].absolute_path == python_file.resolve()


def test_scanner_applies_ignore_and_filter_rules(
    tmp_path: Path,
) -> None:
    """Ignored, binary, oversized and unsupported files are skipped."""

    (tmp_path / ".gitignore").write_text(
        "ignored.py\ngenerated/\n",
        encoding="utf-8",
    )

    (tmp_path / "valid.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    (tmp_path / "ignored.py").write_text(
        "value = 2\n",
        encoding="utf-8",
    )

    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "generated.py").write_text(
        "value = 3\n",
        encoding="utf-8",
    )

    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "dependency.js").write_text(
        "export const dependency = true;\n",
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text(
        "# Repository\n",
        encoding="utf-8",
    )

    (tmp_path / "large.py").write_text(
        "x" * 100,
        encoding="utf-8",
    )

    (tmp_path / "binary.py").write_bytes(
        b"before\x00after",
    )

    scanner = RepositoryScanner(
        RepositoryScannerConfig(
            max_file_size_bytes=50,
        ),
    )

    result = scanner.scan(tmp_path)

    paths = {source_file.relative_path.as_posix() for source_file in result.files}

    assert paths == {"valid.py"}
    assert result.statistics.ignored_file_count == 1
    assert result.statistics.pruned_directory_count >= 2
    assert result.statistics.unsupported_file_count >= 1
    assert result.statistics.oversized_file_count == 1
    assert result.statistics.binary_file_count == 1


def test_scanner_hash_changes_with_content(
    tmp_path: Path,
) -> None:
    """Changed content should produce a different SHA-256 hash."""

    source_file = tmp_path / "service.py"
    source_file.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    scanner = RepositoryScanner()

    first_hash = (
        scanner.scan(
            tmp_path,
        )
        .files[0]
        .content_hash
    )

    source_file.write_text(
        "value = 2\n",
        encoding="utf-8",
    )

    second_hash = (
        scanner.scan(
            tmp_path,
        )
        .files[0]
        .content_hash
    )

    assert first_hash != second_hash
