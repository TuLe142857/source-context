"""Public contracts for incremental repository parsing."""

from dataclasses import dataclass
from enum import StrEnum

from .contracts import ParseResult


class SourceFileChange(StrEnum):
    """How a source file differs from the previous snapshot."""

    ADDED = "added"
    MODIFIED = "modified"


@dataclass(frozen=True, slots=True)
class SourceFileFingerprint:
    """Stable identity of one scanned source-file version."""

    relative_path: str
    content_hash: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""

        return {
            "relative_path": self.relative_path,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class ParsedSourceFile:
    """Parse output for one added or modified source file."""

    relative_path: str
    content_hash: str
    change: SourceFileChange
    parse_result: ParseResult

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable summary."""

        return {
            "relative_path": self.relative_path,
            "content_hash": self.content_hash,
            "change": self.change.value,
            "parse_result": self.parse_result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RepositoryParseBatch:
    """Incremental parse result for one repository snapshot."""

    parsed_files: tuple[ParsedSourceFile, ...]
    unchanged_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    current_files: tuple[SourceFileFingerprint, ...]

    @property
    def current_hashes(self) -> dict[str, str]:
        """Return the snapshot expected by the next run."""

        return {file.relative_path: file.content_hash for file in self.current_files}

    @property
    def changed_paths(self) -> tuple[str, ...]:
        """Return paths that were added or modified."""

        return tuple(file.relative_path for file in self.parsed_files)

    @property
    def has_changes(self) -> bool:
        """Return whether the repository snapshot has changed."""

        return bool(self.parsed_files or self.deleted_paths)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable summary."""

        return {
            "parsed_files": [file.to_dict() for file in self.parsed_files],
            "unchanged_paths": list(
                self.unchanged_paths,
            ),
            "deleted_paths": list(
                self.deleted_paths,
            ),
            "current_files": [file.to_dict() for file in self.current_files],
            "has_changes": self.has_changes,
        }
