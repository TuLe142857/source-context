"""Production source-code chunking package."""

from .contracts import (
    ChunkCoverage,
    ChunkingOptions,
    ChunkingResult,
    ChunkSizeUnit,
    SourceChunk,
)
from .coverage import verify_chunk_coverage
from .exceptions import (
    ChunkCoverageError,
    ChunkingError,
)
from .service import ChunkingService
from .size import (
    ByteSizeMeasurer,
    ChunkSizeMeasurer,
    WordSizeMeasurer,
    get_size_measurer,
    measure_source_range,
)


__all__ = [
    "ByteSizeMeasurer",
    "ChunkCoverage",
    "ChunkingOptions",
    "ChunkingResult",
    "ChunkSizeMeasurer",
    "ChunkSizeUnit",
    "SourceChunk",
    "WordSizeMeasurer",
    "get_size_measurer",
    "measure_source_range",
    "verify_chunk_coverage",
    "ChunkCoverageError",
    "ChunkingError",
    "ChunkingService",
]
