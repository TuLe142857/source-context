"""Incremental parser service for repository scan results."""

from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath, PureWindowsPath

from app.domain.source_file import (
    ScannedSourceFile,
    compute_source_content_hash,
)
from app.schemas.repository import RepositoryScanResult

from .exc import StaleScannedSourceFileError
from .repository_contracts import (
    ParsedSourceFile,
    RepositoryParseBatch,
    SourceFileChange,
    SourceFileFingerprint,
)
from .service import ParserService


class RepositoryParserService:
    """Parse added and modified files from repository scan output."""

    def __init__(
        self,
        parser_service: ParserService | None = None,
    ) -> None:
        self._parser_service = (
            parser_service if parser_service is not None else ParserService()
        )

    @property
    def parser_service(self) -> ParserService:
        """Return the underlying single-file parser service."""

        return self._parser_service

    def parse_scan_result(
        self,
        scan_result: RepositoryScanResult,
        *,
        previous_hashes: Mapping[str, str] | None = None,
    ) -> RepositoryParseBatch:
        """Parse files contained in a RepositoryScanResult."""

        return self.parse_scanned_files(
            scan_result.files,
            previous_hashes=previous_hashes,
        )

    def parse_scanned_files(
        self,
        scanned_files: Iterable[ScannedSourceFile],
        *,
        previous_hashes: Mapping[str, str] | None = None,
    ) -> RepositoryParseBatch:
        """Parse added/modified files and detect deleted files."""

        normalized_previous_hashes = self._normalize_previous_hashes(
            previous_hashes or {},
        )

        ordered_files = sorted(
            scanned_files,
            key=lambda file: file.relative_path.as_posix(),
        )

        parsed_files: list[ParsedSourceFile] = []
        unchanged_paths: list[str] = []
        current_files: list[SourceFileFingerprint] = []
        current_paths: set[str] = set()

        for scanned_file in ordered_files:
            relative_path = self._normalize_relative_path(
                scanned_file.relative_path.as_posix(),
            )

            if relative_path in current_paths:
                raise ValueError(
                    f"Duplicate scanned source path: {relative_path!r}.",
                )

            current_paths.add(
                relative_path,
            )

            current_files.append(
                SourceFileFingerprint(
                    relative_path=relative_path,
                    content_hash=(scanned_file.content_hash),
                ),
            )

            previous_hash = normalized_previous_hashes.get(
                relative_path,
            )

            if previous_hash == scanned_file.content_hash:
                unchanged_paths.append(
                    relative_path,
                )
                continue

            source_bytes = scanned_file.absolute_path.read_bytes()

            actual_hash = compute_source_content_hash(
                source_bytes,
            )

            self._validate_scanned_metadata(
                scanned_file,
                relative_path=relative_path,
                source_bytes=source_bytes,
                actual_hash=actual_hash,
            )

            parse_result = self._parser_service.parse_bytes(
                source_bytes,
                file_path=relative_path,
            )

            if parse_result.language != scanned_file.language.value:
                raise RuntimeError(
                    "Scanner and parser resolved "
                    "different languages for "
                    f"{relative_path!r}: "
                    "scanner="
                    f"{scanned_file.language.value!r}, "
                    "parser="
                    f"{parse_result.language!r}.",
                )

            change = (
                SourceFileChange.ADDED
                if previous_hash is None
                else SourceFileChange.MODIFIED
            )

            parsed_files.append(
                ParsedSourceFile(
                    relative_path=relative_path,
                    content_hash=(scanned_file.content_hash),
                    change=change,
                    parse_result=parse_result,
                ),
            )

        deleted_paths = tuple(
            sorted(
                set(
                    normalized_previous_hashes,
                )
                - current_paths,
            ),
        )

        return RepositoryParseBatch(
            parsed_files=tuple(
                parsed_files,
            ),
            unchanged_paths=tuple(
                unchanged_paths,
            ),
            deleted_paths=deleted_paths,
            current_files=tuple(
                current_files,
            ),
        )

    @staticmethod
    def _validate_scanned_metadata(
        scanned_file: ScannedSourceFile,
        *,
        relative_path: str,
        source_bytes: bytes,
        actual_hash: str,
    ) -> None:
        """Ensure source still matches the scanner snapshot."""

        actual_size = len(
            source_bytes,
        )

        if (
            actual_size == scanned_file.size_bytes
            and actual_hash == scanned_file.content_hash
        ):
            return

        raise StaleScannedSourceFileError(
            relative_path,
            expected_size=(scanned_file.size_bytes),
            actual_size=actual_size,
            expected_hash=(scanned_file.content_hash),
            actual_hash=actual_hash,
        )

    @classmethod
    def _normalize_previous_hashes(
        cls,
        previous_hashes: Mapping[str, str],
    ) -> dict[str, str]:
        """Normalize and validate a previous snapshot."""

        normalized: dict[str, str] = {}

        for path, content_hash in previous_hashes.items():
            normalized_path = cls._normalize_relative_path(
                path,
            )

            existing_hash = normalized.get(
                normalized_path,
            )

            if existing_hash is not None and existing_hash != content_hash:
                raise ValueError(
                    f"Conflicting hashes for normalized path {normalized_path!r}.",
                )

            normalized[normalized_path] = content_hash

        return normalized

    @staticmethod
    def _normalize_relative_path(
        value: str,
    ) -> str:
        """Normalize a repository-relative path to POSIX form."""

        stripped_value = value.strip()

        if not stripped_value:
            raise ValueError(
                "Source path must not be empty.",
            )

        windows_path = PureWindowsPath(
            stripped_value,
        )

        normalized_value = stripped_value.replace(
            "\\",
            "/",
        )
        posix_path = PurePosixPath(
            normalized_value,
        )

        if (
            windows_path.drive
            or windows_path.is_absolute()
            or posix_path.is_absolute()
            or posix_path.as_posix() == "."
            or ".." in posix_path.parts
        ):
            raise ValueError(
                f"Expected a repository-relative source path, received {value!r}.",
            )

        return posix_path.as_posix()
