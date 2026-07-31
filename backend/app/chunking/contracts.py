"""Public contracts for source-code chunking."""

from dataclasses import dataclass
from enum import StrEnum


class ChunkSizeUnit(StrEnum):
    """Supported chunk-size measurement units."""

    BYTE = "byte"
    WORD = "word"


@dataclass(frozen=True, slots=True)
class ChunkingOptions:
    """Configuration used by the chunking pipeline."""

    max_size: int = 500
    size_unit: ChunkSizeUnit = ChunkSizeUnit.BYTE
    merge_adjacent: bool = True
    verify_coverage: bool = True

    def __post_init__(self) -> None:
        if self.max_size <= 0:
            raise ValueError(
                "max_size must be greater than zero",
            )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "max_size": self.max_size,
            "size_unit": self.size_unit.value,
            "merge_adjacent": self.merge_adjacent,
            "verify_coverage": self.verify_coverage,
        }


@dataclass(frozen=True, slots=True)
class SourceChunk:
    """One exact source-code byte range."""

    index: int
    file_path: str
    language: str
    parser_name: str
    start_byte: int
    end_byte: int
    size: int
    content: str
    symbol_name: str | None = None
    symbol_kind: str | None = None

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(
                "index must not be negative",
            )

        if self.start_byte < 0:
            raise ValueError(
                "start_byte must not be negative",
            )

        if self.end_byte <= self.start_byte:
            raise ValueError(
                "end_byte must be greater than start_byte",
            )

        if self.size < 0:
            raise ValueError(
                "size must not be negative",
            )

    @property
    def byte_size(self) -> int:
        """Return the source span size in bytes."""

        return self.end_byte - self.start_byte

    def to_dict(
        self,
        *,
        include_content: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        payload: dict[str, object] = {
            "index": self.index,
            "file_path": self.file_path,
            "language": self.language,
            "parser_name": self.parser_name,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "byte_size": self.byte_size,
            "size": self.size,
            "symbol_name": self.symbol_name,
            "symbol_kind": self.symbol_kind,
        }

        if include_content:
            payload["content"] = self.content

        return payload


@dataclass(frozen=True, slots=True)
class ChunkCoverage:
    """Result of exact source-coverage verification."""

    total_bytes: int
    covered_bytes: int
    missing_bytes: int
    overlap_bytes: int
    issues: tuple[str, ...]

    @property
    def is_exact(self) -> bool:
        """Return whether chunks cover the source exactly once."""

        return (
            not self.issues
            and self.covered_bytes == self.total_bytes
            and self.missing_bytes == 0
            and self.overlap_bytes == 0
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "total_bytes": self.total_bytes,
            "covered_bytes": self.covered_bytes,
            "missing_bytes": self.missing_bytes,
            "overlap_bytes": self.overlap_bytes,
            "issues": list(self.issues),
            "is_exact": self.is_exact,
        }


@dataclass(frozen=True, slots=True)
class ChunkingResult:
    """Normalized output returned by ChunkingService."""

    file_path: str
    language: str
    parser_name: str
    options: ChunkingOptions
    chunks: tuple[SourceChunk, ...]
    coverage: ChunkCoverage

    @property
    def chunk_count(self) -> int:
        """Return the number of generated chunks."""

        return len(self.chunks)

    @property
    def over_limit_count(self) -> int:
        """Return the number of chunks exceeding the configured limit."""

        return sum(chunk.size > self.options.max_size for chunk in self.chunks)

    def to_dict(
        self,
        *,
        include_content: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-serializable result summary."""

        return {
            "file_path": self.file_path,
            "language": self.language,
            "parser_name": self.parser_name,
            "options": self.options.to_dict(),
            "chunk_count": self.chunk_count,
            "over_limit_count": self.over_limit_count,
            "coverage": self.coverage.to_dict(),
            "chunks": [
                chunk.to_dict(
                    include_content=include_content,
                )
                for chunk in self.chunks
            ],
        }
