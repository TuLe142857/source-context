"""Contracts for repository-level source chunking."""

from dataclasses import dataclass

from app.parser.repository_contracts import (
    SourceFileChange,
    SourceFileFingerprint,
)

from .contracts import ChunkingResult


@dataclass(frozen=True, slots=True)
class ChunkedSourceFile:
    """Chunking output for one added or modified source file."""

    relative_path: str
    content_hash: str
    change: SourceFileChange
    chunking_result: ChunkingResult

    @property
    def chunk_count(self) -> int:
        """Return the number of chunks generated for this file."""

        return self.chunking_result.chunk_count

    def to_dict(
        self,
        *,
        include_content: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "relative_path": self.relative_path,
            "content_hash": self.content_hash,
            "change": self.change.value,
            "chunk_count": self.chunk_count,
            "chunking_result": self.chunking_result.to_dict(
                include_content=include_content,
            ),
        }


@dataclass(frozen=True, slots=True)
class RepositoryChunkingBatch:
    """Repository output after chunking changed source files."""

    chunked_files: tuple[ChunkedSourceFile, ...]
    unchanged_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    current_files: tuple[SourceFileFingerprint, ...]

    @property
    def changed_paths(self) -> tuple[str, ...]:
        """Return paths that were added or modified."""

        return tuple(chunked_file.relative_path for chunked_file in self.chunked_files)

    @property
    def chunk_count(self) -> int:
        """Return the total number of generated chunks."""

        return sum(chunked_file.chunk_count for chunked_file in self.chunked_files)

    @property
    def current_hashes(self) -> dict[str, str]:
        """Return the current repository file-hash snapshot."""

        return {
            fingerprint.relative_path: fingerprint.content_hash
            for fingerprint in self.current_files
        }

    @property
    def has_changes(self) -> bool:
        """Return whether downstream indexes need updating."""

        return bool(self.chunked_files or self.deleted_paths)

    def to_dict(
        self,
        *,
        include_content: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-serializable batch representation."""

        return {
            "chunked_files": [
                chunked_file.to_dict(
                    include_content=include_content,
                )
                for chunked_file in self.chunked_files
            ],
            "changed_paths": list(
                self.changed_paths,
            ),
            "unchanged_paths": list(
                self.unchanged_paths,
            ),
            "deleted_paths": list(
                self.deleted_paths,
            ),
            "current_hashes": self.current_hashes,
            "chunk_count": self.chunk_count,
            "has_changes": self.has_changes,
        }
