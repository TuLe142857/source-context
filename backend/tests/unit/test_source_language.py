"""Tests for canonical source-language detection."""

from pathlib import Path

import pytest

from app.domain.source_file import (
    SOURCE_LANGUAGE_BY_EXTENSION,
    SOURCE_LANGUAGE_EXTENSIONS,
    SourceLanguage,
    detect_source_language,
)


@pytest.mark.parametrize(
    ("file_name", "expected_language"),
    [
        ("service.py", SourceLanguage.PYTHON),
        ("types.pyi", SourceLanguage.PYTHON),
        ("index.js", SourceLanguage.JAVASCRIPT),
        ("component.jsx", SourceLanguage.JAVASCRIPT),
        ("package.mjs", SourceLanguage.JAVASCRIPT),
        ("config.cjs", SourceLanguage.JAVASCRIPT),
        ("service.ts", SourceLanguage.TYPESCRIPT),
        ("component.tsx", SourceLanguage.TYPESCRIPT),
        ("module.mts", SourceLanguage.TYPESCRIPT),
        ("config.cts", SourceLanguage.TYPESCRIPT),
    ],
)
def test_detect_source_language(
    file_name: str,
    expected_language: SourceLanguage,
) -> None:
    """Supported extensions should resolve to their canonical language."""

    assert detect_source_language(file_name) is expected_language


@pytest.mark.parametrize(
    "file_name",
    [
        "SERVICE.PY",
        "COMPONENT.JSX",
        "MODULE.TS",
        "COMPONENT.TSX",
    ],
)
def test_detect_source_language_case_insensitively(
    file_name: str,
) -> None:
    """Extension detection should not depend on letter casing."""

    assert detect_source_language(file_name) is not None


@pytest.mark.parametrize(
    "file_name",
    [
        "README.md",
        "Dockerfile",
        "service.java",
        "main.go",
        "program.cs",
        "file_without_extension",
    ],
)
def test_detect_source_language_returns_none_for_unsupported_file(
    file_name: str,
) -> None:
    """Files outside the active parser scope should not resolve."""

    assert detect_source_language(file_name) is None


def test_language_extensions_are_unique() -> None:
    """No extension may belong to multiple canonical languages."""

    all_extensions = [
        extension
        for extensions in SOURCE_LANGUAGE_EXTENSIONS.values()
        for extension in extensions
    ]

    assert len(all_extensions) == len(set(all_extensions))
    assert len(SOURCE_LANGUAGE_BY_EXTENSION) == len(all_extensions)


def test_detect_source_language_accepts_path_objects() -> None:
    """Detection should accept Path as well as string input."""

    file_path = Path("src") / "application.py"

    assert detect_source_language(file_path) is SourceLanguage.PYTHON
