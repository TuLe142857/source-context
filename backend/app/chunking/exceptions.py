"""Exceptions raised by the production chunking pipeline."""

from .contracts import ChunkCoverage


class ChunkingError(RuntimeError):
    """Base exception for chunking failures."""


class ChunkCoverageError(ChunkingError):
    """Raised when generated chunks violate coverage invariants."""

    def __init__(
        self,
        coverage: ChunkCoverage,
    ) -> None:
        self.coverage = coverage

        issue_summary = (
            "; ".join(
                coverage.issues,
            )
            if coverage.issues
            else "unknown coverage inconsistency"
        )

        super().__init__(
            f"Generated chunks do not cover the source exactly: {issue_summary}",
        )
