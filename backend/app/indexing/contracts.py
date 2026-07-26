"""Provider-neutral contracts for code indexing."""

from dataclasses import dataclass
from enum import StrEnum


_HEXADECIMAL_CHARACTERS = frozenset(
    "0123456789abcdef",
)


def _validate_non_empty(
    field_name: str,
    value: str,
) -> None:
    """Validate one required string field."""

    if not value.strip():
        raise ValueError(
            f"{field_name} must not be empty",
        )


def _validate_sha256(
    field_name: str,
    value: str,
) -> None:
    """Validate a lowercase SHA-256 hexadecimal digest."""

    if len(value) != 64 or any(
        character not in _HEXADECIMAL_CHARACTERS for character in value
    ):
        raise ValueError(
            f"{field_name} must be a lowercase SHA-256 digest",
        )


class IndexDeleteReason(StrEnum):
    """Reason for deleting all indexed records belonging to a file."""

    REPLACE_FILE = "replace_file"
    SOURCE_DELETED = "source_deleted"


@dataclass(frozen=True, slots=True)
class IndexingDocument:
    """One chunk transformed into a provider-neutral index document."""

    document_id: str
    repository_id: str
    revision: str
    file_path: str
    content_hash: str

    chunk_index: int
    text: str

    language: str
    parser_name: str
    source_change: str

    start_byte: int
    end_byte: int

    size: int
    size_unit: str

    symbol_name: str | None = None
    symbol_kind: str | None = None

    def __post_init__(self) -> None:
        _validate_sha256(
            "document_id",
            self.document_id,
        )
        _validate_sha256(
            "content_hash",
            self.content_hash,
        )

        for field_name, value in (
            (
                "repository_id",
                self.repository_id,
            ),
            (
                "revision",
                self.revision,
            ),
            (
                "file_path",
                self.file_path,
            ),
            (
                "language",
                self.language,
            ),
            (
                "parser_name",
                self.parser_name,
            ),
            (
                "source_change",
                self.source_change,
            ),
            (
                "size_unit",
                self.size_unit,
            ),
        ):
            _validate_non_empty(
                field_name,
                value,
            )

        if self.chunk_index < 0:
            raise ValueError(
                "chunk_index must not be negative",
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
        """Return the raw byte length represented by the document."""

        return self.end_byte - self.start_byte

    def to_dict(
        self,
        *,
        include_text: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        payload: dict[str, object] = {
            "document_id": self.document_id,
            "repository_id": self.repository_id,
            "revision": self.revision,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "chunk_index": self.chunk_index,
            "language": self.language,
            "parser_name": self.parser_name,
            "source_change": self.source_change,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "byte_size": self.byte_size,
            "size": self.size,
            "size_unit": self.size_unit,
            "symbol_name": self.symbol_name,
            "symbol_kind": self.symbol_kind,
        }

        if include_text:
            payload["text"] = self.text

        return payload


@dataclass(frozen=True, slots=True)
class DeleteFileIndexOperation:
    """Delete all indexed records belonging to one source path."""

    repository_id: str
    revision: str
    file_path: str
    reason: IndexDeleteReason

    def __post_init__(self) -> None:
        _validate_non_empty(
            "repository_id",
            self.repository_id,
        )
        _validate_non_empty(
            "revision",
            self.revision,
        )
        _validate_non_empty(
            "file_path",
            self.file_path,
        )

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""

        return {
            "repository_id": self.repository_id,
            "revision": self.revision,
            "file_path": self.file_path,
            "reason": self.reason.value,
        }


@dataclass(frozen=True, slots=True)
class IndexingFileSnapshot:
    """One file entry in the current repository snapshot."""

    file_path: str
    content_hash: str

    def __post_init__(self) -> None:
        _validate_non_empty(
            "file_path",
            self.file_path,
        )
        _validate_sha256(
            "content_hash",
            self.content_hash,
        )

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""

        return {
            "file_path": self.file_path,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class IndexingPlan:
    """Provider-neutral operations produced for one repository revision."""

    repository_id: str
    revision: str

    documents: tuple[IndexingDocument, ...]
    delete_operations: tuple[
        DeleteFileIndexOperation,
        ...,
    ]

    changed_paths: tuple[str, ...]
    unchanged_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]

    current_files: tuple[
        IndexingFileSnapshot,
        ...,
    ]

    def __post_init__(self) -> None:
        _validate_non_empty(
            "repository_id",
            self.repository_id,
        )
        _validate_non_empty(
            "revision",
            self.revision,
        )

    @property
    def document_count(self) -> int:
        """Return the number of documents requiring embedding."""

        return len(
            self.documents,
        )

    @property
    def delete_operation_count(self) -> int:
        """Return the number of file-level delete operations."""

        return len(
            self.delete_operations,
        )

    @property
    def current_hashes(self) -> dict[str, str]:
        """Return the current repository snapshot as a mapping."""

        return {
            file_snapshot.file_path: (file_snapshot.content_hash)
            for file_snapshot in self.current_files
        }

    @property
    def has_operations(self) -> bool:
        """Return whether a downstream index must be changed."""

        return bool(self.documents or self.delete_operations)

    def to_dict(
        self,
        *,
        include_text: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-serializable plan representation."""

        return {
            "repository_id": self.repository_id,
            "revision": self.revision,
            "documents": [
                document.to_dict(
                    include_text=include_text,
                )
                for document in self.documents
            ],
            "delete_operations": [
                operation.to_dict() for operation in (self.delete_operations)
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
            "current_files": [
                file_snapshot.to_dict() for file_snapshot in (self.current_files)
            ],
            "current_hashes": self.current_hashes,
            "document_count": self.document_count,
            "delete_operation_count": (self.delete_operation_count),
            "has_operations": self.has_operations,
        }
