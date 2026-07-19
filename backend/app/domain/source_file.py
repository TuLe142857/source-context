"""Domain models representing scanned source files."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


class SourceLanguage(StrEnum):
    """Programming languages supported by the initial indexing pipeline."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


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

        return self.repository_root.joinpath(*self.relative_path.parts)
