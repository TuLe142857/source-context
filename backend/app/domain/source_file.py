"""Domain models and language metadata for scanned source files."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Final, Mapping


class SourceLanguage(StrEnum):
    """Canonical programming languages supported by the indexing pipeline."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


SOURCE_LANGUAGE_EXTENSIONS: Final[Mapping[SourceLanguage, tuple[str, ...]]] = {
    SourceLanguage.PYTHON: (
        ".py",
        ".pyi",
    ),
    SourceLanguage.JAVASCRIPT: (
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
    ),
    SourceLanguage.TYPESCRIPT: (
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
    ),
}
"""Canonical file extensions supported for each source language."""


SOURCE_LANGUAGE_BY_EXTENSION: Final[Mapping[str, SourceLanguage]] = {
    extension: language
    for language, extensions in SOURCE_LANGUAGE_EXTENSIONS.items()
    for extension in extensions
}
"""Reverse lookup from normalized extension to source language."""


def detect_source_language(
    file_path: str | Path,
) -> SourceLanguage | None:
    """Detect a supported source language from a file path.

    File extensions are matched case-insensitively.
    """

    extension = Path(file_path).suffix.casefold()
    return SOURCE_LANGUAGE_BY_EXTENSION.get(extension)


@dataclass(frozen=True, slots=True)
class ScannedSourceFile:
    """Metadata for a source file discovered inside a repository."""

    repository_root: Path
    relative_path: PurePosixPath
    language: SourceLanguage
    size_bytes: int
    content_hash: str

    @property
    def absolute_path(self) -> Path:
        """Return the absolute path to the scanned source file."""

        return self.repository_root.joinpath(
            *self.relative_path.parts,
        )
