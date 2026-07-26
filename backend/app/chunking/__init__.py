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
    RepositoryChunkingError,
)
from .service import ChunkingService
from .size import (
    ByteSizeMeasurer,
    ChunkSizeMeasurer,
    WordSizeMeasurer,
    get_size_measurer,
    measure_source_range,
)

from .repository_contracts import (
    ChunkedSourceFile,
    RepositoryChunkingBatch,
)
from .repository_service import (
    RepositoryChunkingService,
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
    "ChunkedSourceFile",
    "RepositoryChunkingBatch",
    "RepositoryChunkingError",
    "RepositoryChunkingService",
]
