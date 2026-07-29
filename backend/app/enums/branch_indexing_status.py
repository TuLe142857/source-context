"""Enumeration for branch indexing status."""

from enum import StrEnum


class BranchIndexingStatus(StrEnum):
    """Indexing status for repository branches."""

    UNINDEXED = "UNINDEXED"
    INDEXING = "INDEXING"
    INDEXED = "INDEXED"
    OUTDATED = "OUTDATED"
    FAILED = "FAILED"
