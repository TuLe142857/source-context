"""Exceptions raised while building indexing plans."""


class IndexingError(RuntimeError):
    """Base exception for indexing pipeline failures."""


class IndexingContractError(IndexingError):
    """Raised when an upstream batch violates indexing contracts."""
