"""Provider-neutral source-code indexing contracts."""

from .builder import (
    IndexingDocumentBuilder,
)
from .contracts import (
    DeleteFileIndexOperation,
    IndexDeleteReason,
    IndexingDocument,
    IndexingFileSnapshot,
    IndexingPlan,
)
from .exceptions import (
    IndexingContractError,
    IndexingError,
)
from .ids import (
    compute_indexing_document_id,
)

__all__ = [
    "DeleteFileIndexOperation",
    "IndexDeleteReason",
    "IndexingContractError",
    "IndexingDocument",
    "IndexingDocumentBuilder",
    "IndexingError",
    "IndexingFileSnapshot",
    "IndexingPlan",
    "compute_indexing_document_id",
]
