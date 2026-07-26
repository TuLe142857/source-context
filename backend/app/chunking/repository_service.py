"""Repository-level orchestration for production chunking."""

from pathlib import (
    PurePosixPath,
    PureWindowsPath,
)

from app.domain.source_file import (
    compute_source_content_hash,
)
from app.parser.repository_contracts import (
    ParsedSourceFile,
    RepositoryParseBatch,
)
from app.parser.uast import ContainerNode

from .contracts import ChunkingOptions
from .exceptions import RepositoryChunkingError
from .repository_contracts import (
    ChunkedSourceFile,
    RepositoryChunkingBatch,
)
from .service import ChunkingService


class RepositoryChunkingService:
    """Chunk all added and modified files in a parse batch."""

    def __init__(
        self,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self._chunking_service = (
            chunking_service if chunking_service is not None else ChunkingService()
        )

    def chunk_parse_batch(
        self,
        parse_batch: RepositoryParseBatch,
        *,
        options: ChunkingOptions | None = None,
    ) -> RepositoryChunkingBatch:
        """Chunk changed files and propagate unchanged/deleted paths."""

        resolved_options = options if options is not None else ChunkingOptions()

        chunked_files: list[ChunkedSourceFile] = []
        seen_paths: set[str] = set()

        sorted_parsed_files = sorted(
            parse_batch.parsed_files,
            key=lambda parsed_file: self._normalize_relative_path(
                parsed_file.relative_path,
            ),
        )

        for parsed_file in sorted_parsed_files:
            relative_path = self._normalize_relative_path(
                parsed_file.relative_path,
            )

            if relative_path in seen_paths:
                raise RepositoryChunkingError(
                    "Duplicate parsed source path in repository batch: "
                    f"{relative_path}",
                )

            seen_paths.add(
                relative_path,
            )

            self._validate_parsed_file(
                parsed_file,
                expected_path=relative_path,
            )

            chunking_result = self._chunking_service.chunk_parse_result(
                parsed_file.parse_result,
                options=resolved_options,
            )

            result_path = self._normalize_relative_path(
                chunking_result.file_path,
            )

            if result_path != relative_path:
                raise RepositoryChunkingError(
                    "Chunking result path does not match parsed source path: "
                    f"expected={relative_path}, "
                    f"received={result_path}",
                )

            chunked_files.append(
                ChunkedSourceFile(
                    relative_path=relative_path,
                    content_hash=parsed_file.content_hash,
                    change=parsed_file.change,
                    chunking_result=chunking_result,
                ),
            )

        unchanged_paths = tuple(
            sorted(
                self._normalize_relative_path(path)
                for path in parse_batch.unchanged_paths
            ),
        )

        deleted_paths = tuple(
            sorted(
                self._normalize_relative_path(path)
                for path in parse_batch.deleted_paths
            ),
        )

        current_files = tuple(
            sorted(
                parse_batch.current_files,
                key=lambda fingerprint: self._normalize_relative_path(
                    fingerprint.relative_path,
                ),
            ),
        )

        return RepositoryChunkingBatch(
            chunked_files=tuple(
                chunked_files,
            ),
            unchanged_paths=unchanged_paths,
            deleted_paths=deleted_paths,
            current_files=current_files,
        )

    @staticmethod
    def _validate_parsed_file(
        parsed_file: ParsedSourceFile,
        *,
        expected_path: str,
    ) -> None:
        """Validate source bytes, hash and parser path consistency."""

        parse_result = parsed_file.parse_result

        parse_result_path = RepositoryChunkingService._normalize_relative_path(
            parse_result.file_path,
        )

        if parse_result_path != expected_path:
            raise RepositoryChunkingError(
                "ParseResult path does not match ParsedSourceFile path: "
                f"expected={expected_path}, "
                f"received={parse_result_path}",
            )

        uast_root = parse_result.uast_root

        if not isinstance(
            uast_root,
            ContainerNode,
        ):
            raise RepositoryChunkingError(
                f"Parsed source UAST root must be a ContainerNode: {expected_path}",
            )

        source_bytes = uast_root.source_bytes

        if source_bytes is None:
            raise RepositoryChunkingError(
                f"Parsed source does not contain source bytes: {expected_path}",
            )

        actual_hash = compute_source_content_hash(
            source_bytes,
        )

        if actual_hash != parsed_file.content_hash:
            raise RepositoryChunkingError(
                "Parsed source content hash does not match batch metadata: "
                f"path={expected_path}, "
                f"expected={parsed_file.content_hash}, "
                f"actual={actual_hash}",
            )

    @staticmethod
    def _normalize_relative_path(
        path: str | PurePosixPath,
    ) -> str:
        """Normalize and validate one repository-relative path."""

        raw_path = str(
            path,
        ).replace(
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
            raise RepositoryChunkingError(
                "Repository chunking paths must be relative and "
                f"must not traverse parents: {path}",
            )

        normalized_path = posix_path.as_posix()

        if normalized_path in {
            "",
            ".",
        }:
            raise RepositoryChunkingError(
                "Repository chunking path must not be empty.",
            )

        return normalized_path
