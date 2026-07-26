"""Deterministic identifiers for indexing documents."""

from hashlib import sha256
from typing import Final


_DOCUMENT_ID_VERSION: Final = "index-document-v1"


def compute_indexing_document_id(
    *,
    repository_id: str,
    file_path: str,
    content_hash: str,
    chunk_index: int,
    start_byte: int,
    end_byte: int,
) -> str:
    """Return a stable SHA-256 identifier for one source chunk.

    Revision is deliberately excluded. The same repository, path,
    content and chunk boundary produce the same document identity
    across repeated indexing jobs.
    """

    identity_parts = (
        _DOCUMENT_ID_VERSION,
        repository_id,
        file_path,
        content_hash,
        str(
            chunk_index,
        ),
        str(
            start_byte,
        ),
        str(
            end_byte,
        ),
    )

    canonical_identity = "\0".join(
        identity_parts,
    ).encode(
        "utf-8",
    )

    return sha256(
        canonical_identity,
    ).hexdigest()
