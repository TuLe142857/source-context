"""Build provider-neutral indexing plans from chunking batches."""

from collections.abc import Mapping
from pathlib import (
    PurePosixPath,
    PureWindowsPath,
)

from app.chunking import (
    RepositoryChunkingBatch,
    SourceChunk,
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
)
from .ids import (
    compute_indexing_document_id,
)


class IndexingDocumentBuilder:
    """Transform repository chunking output into indexing operations."""

    def build(
        self,
        chunking_batch: RepositoryChunkingBatch,
        *,
        repository_id: str,
        revision: str,
    ) -> IndexingPlan:
        """Build deterministic documents and file-delete operations."""

        normalized_repository_id = repository_id.strip()
        normalized_revision = revision.strip()

        if not normalized_repository_id:
            raise IndexingContractError(
                "repository_id must not be empty",
            )

        if not normalized_revision:
            raise IndexingContractError(
                "revision must not be empty",
            )

        current_hashes = self._normalize_current_hashes(
            chunking_batch.current_hashes,
        )

        chunked_files_by_path = {}

        for chunked_file in chunking_batch.chunked_files:
            file_path = self._normalize_path(
                chunked_file.relative_path,
            )

            if file_path in chunked_files_by_path:
                raise IndexingContractError(
                    f"Duplicate changed source path: {file_path}",
                )

            chunked_files_by_path[file_path] = chunked_file

        changed_paths = set(
            chunked_files_by_path,
        )
        unchanged_paths = set(
            self._normalize_paths(
                chunking_batch.unchanged_paths,
            ),
        )
        deleted_paths = set(
            self._normalize_paths(
                chunking_batch.deleted_paths,
            ),
        )

        self._validate_path_sets(
            changed_paths=changed_paths,
            unchanged_paths=unchanged_paths,
            deleted_paths=deleted_paths,
        )

        expected_current_paths = changed_paths | unchanged_paths
        actual_current_paths = set(
            current_hashes,
        )

        if expected_current_paths != actual_current_paths:
            missing_paths = sorted(
                expected_current_paths - actual_current_paths,
            )
            unexpected_paths = sorted(
                actual_current_paths - expected_current_paths,
            )

            raise IndexingContractError(
                "Current file snapshot does not match "
                "changed and unchanged paths: "
                f"missing={missing_paths}, "
                f"unexpected={unexpected_paths}",
            )

        documents: list[IndexingDocument] = []
        delete_operations: list[DeleteFileIndexOperation] = []

        for file_path in sorted(
            chunked_files_by_path,
        ):
            chunked_file = chunked_files_by_path[file_path]

            expected_hash = current_hashes[file_path]

            if chunked_file.content_hash != expected_hash:
                raise IndexingContractError(
                    "Changed source hash does not match "
                    "the current repository snapshot: "
                    f"path={file_path}, "
                    f"changed_hash="
                    f"{chunked_file.content_hash}, "
                    f"snapshot_hash={expected_hash}",
                )

            chunking_result = chunked_file.chunking_result

            result_path = self._normalize_path(
                chunking_result.file_path,
            )

            if result_path != file_path:
                raise IndexingContractError(
                    "Chunking result path does not match "
                    "the changed source path: "
                    f"expected={file_path}, "
                    f"received={result_path}",
                )

            if not chunking_result.coverage.is_exact:
                raise IndexingContractError(
                    f"Cannot index chunks with non-exact coverage: {file_path}",
                )

            if chunking_result.over_limit_count != 0:
                raise IndexingContractError(
                    f"Cannot index chunks that exceed the size limit: {file_path}",
                )

            delete_operations.append(
                DeleteFileIndexOperation(
                    repository_id=(normalized_repository_id),
                    revision=(normalized_revision),
                    file_path=file_path,
                    reason=(IndexDeleteReason.REPLACE_FILE),
                ),
            )

            documents.extend(
                self._build_file_documents(
                    repository_id=(normalized_repository_id),
                    revision=(normalized_revision),
                    file_path=file_path,
                    content_hash=(chunked_file.content_hash),
                    source_change=(chunked_file.change.value),
                    chunks=(chunking_result.chunks),
                    language=(chunking_result.language),
                    parser_name=(chunking_result.parser_name),
                    size_unit=(chunking_result.options.size_unit.value),
                ),
            )

        for file_path in sorted(
            deleted_paths,
        ):
            delete_operations.append(
                DeleteFileIndexOperation(
                    repository_id=(normalized_repository_id),
                    revision=(normalized_revision),
                    file_path=file_path,
                    reason=(IndexDeleteReason.SOURCE_DELETED),
                ),
            )

        current_files = tuple(
            IndexingFileSnapshot(
                file_path=file_path,
                content_hash=current_hashes[file_path],
            )
            for file_path in sorted(
                current_hashes,
            )
        )

        return IndexingPlan(
            repository_id=(normalized_repository_id),
            revision=normalized_revision,
            documents=tuple(
                documents,
            ),
            delete_operations=tuple(
                delete_operations,
            ),
            changed_paths=tuple(
                sorted(
                    changed_paths,
                ),
            ),
            unchanged_paths=tuple(
                sorted(
                    unchanged_paths,
                ),
            ),
            deleted_paths=tuple(
                sorted(
                    deleted_paths,
                ),
            ),
            current_files=current_files,
        )

    def _build_file_documents(
        self,
        *,
        repository_id: str,
        revision: str,
        file_path: str,
        content_hash: str,
        source_change: str,
        chunks: tuple[SourceChunk, ...],
        language: str,
        parser_name: str,
        size_unit: str,
    ) -> list[IndexingDocument]:
        """Convert all chunks belonging to one source file."""

        documents: list[IndexingDocument] = []

        for expected_index, chunk in enumerate(
            chunks,
        ):
            self._validate_chunk(
                chunk,
                expected_index=expected_index,
                expected_path=file_path,
                expected_language=language,
                expected_parser_name=(parser_name),
            )

            documents.append(
                IndexingDocument(
                    document_id=(
                        compute_indexing_document_id(
                            repository_id=(repository_id),
                            file_path=file_path,
                            content_hash=(content_hash),
                            chunk_index=(chunk.index),
                            start_byte=(chunk.start_byte),
                            end_byte=(chunk.end_byte),
                        )
                    ),
                    repository_id=repository_id,
                    revision=revision,
                    file_path=file_path,
                    content_hash=content_hash,
                    chunk_index=chunk.index,
                    text=chunk.content,
                    language=language,
                    parser_name=parser_name,
                    source_change=source_change,
                    start_byte=(chunk.start_byte),
                    end_byte=chunk.end_byte,
                    size=chunk.size,
                    size_unit=size_unit,
                    symbol_name=(chunk.symbol_name),
                    symbol_kind=(chunk.symbol_kind),
                ),
            )

        return documents

    @staticmethod
    def _validate_chunk(
        chunk: SourceChunk,
        *,
        expected_index: int,
        expected_path: str,
        expected_language: str,
        expected_parser_name: str,
    ) -> None:
        """Validate one chunk before creating an index document."""

        if chunk.index != expected_index:
            raise IndexingContractError(
                "Chunk indexes must be consecutive: "
                f"expected={expected_index}, "
                f"received={chunk.index}",
            )

        chunk_path = IndexingDocumentBuilder._normalize_path(
            chunk.file_path,
        )

        if chunk_path != expected_path:
            raise IndexingContractError(
                "Chunk file path does not match "
                "its parent file: "
                f"expected={expected_path}, "
                f"received={chunk_path}",
            )

        if chunk.language != expected_language:
            raise IndexingContractError(
                "Chunk language does not match "
                "its ChunkingResult: "
                f"expected={expected_language}, "
                f"received={chunk.language}",
            )

        if chunk.parser_name != expected_parser_name:
            raise IndexingContractError(
                "Chunk parser name does not match "
                "its ChunkingResult: "
                f"expected={expected_parser_name}, "
                f"received={chunk.parser_name}",
            )

    @staticmethod
    def _validate_path_sets(
        *,
        changed_paths: set[str],
        unchanged_paths: set[str],
        deleted_paths: set[str],
    ) -> None:
        """Ensure file-state categories are mutually exclusive."""

        intersections = {
            "changed_and_unchanged": (changed_paths & unchanged_paths),
            "changed_and_deleted": (changed_paths & deleted_paths),
            "unchanged_and_deleted": (unchanged_paths & deleted_paths),
        }

        conflicts = {
            category: sorted(
                paths,
            )
            for category, paths in (intersections.items())
            if paths
        }

        if conflicts:
            raise IndexingContractError(
                f"Repository file-state categories overlap: {conflicts}",
            )

    @staticmethod
    def _normalize_current_hashes(
        current_hashes: Mapping[
            str,
            str,
        ],
    ) -> dict[str, str]:
        """Normalize current snapshot paths and reject collisions."""

        normalized_hashes: dict[
            str,
            str,
        ] = {}

        for raw_path, content_hash in current_hashes.items():
            normalized_path = IndexingDocumentBuilder._normalize_path(
                raw_path,
            )

            existing_hash = normalized_hashes.get(
                normalized_path,
            )

            if existing_hash is not None and existing_hash != content_hash:
                raise IndexingContractError(
                    "Conflicting hashes after path "
                    "normalization: "
                    f"path={normalized_path}",
                )

            normalized_hashes[normalized_path] = content_hash

        return normalized_hashes

    @staticmethod
    def _normalize_paths(
        paths: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Normalize a tuple of repository-relative paths."""

        normalized_paths = tuple(
            IndexingDocumentBuilder._normalize_path(
                path,
            )
            for path in paths
        )

        if len(set(normalized_paths)) != len(normalized_paths):
            raise IndexingContractError(
                "Duplicate repository paths after normalization",
            )

        return normalized_paths

    @staticmethod
    def _normalize_path(
        path: str,
    ) -> str:
        """Normalize and validate one repository-relative path."""

        raw_path = path.replace(
            "\\",
            "/",
        )

        windows_path = PureWindowsPath(
            raw_path,
        )
        posix_path = PurePosixPath(
            raw_path,
        )

        if (
            windows_path.is_absolute()
            or bool(windows_path.drive)
            or posix_path.is_absolute()
            or ".." in posix_path.parts
        ):
            raise IndexingContractError(
                "Indexing paths must be relative "
                "and must not traverse parents: "
                f"{path}",
            )

        normalized_path = posix_path.as_posix()

        if normalized_path in {
            "",
            ".",
        }:
            raise IndexingContractError(
                "Indexing path must not be empty",
            )

        return normalized_path
