"""Scanner for supported source files in a local repository."""

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.domain.repository import (
    RepositoryScanResult,
    RepositoryScanStatistics,
)
from app.domain.source_file import (
    ScannedSourceFile,
    SourceLanguage,
)
from app.repository_manager.exceptions import (
    InvalidRepositoryPathError,
    RepositoryNotFoundError,
    RepositoryTraversalError,
)
from app.repository_manager.ignore_rules import IgnoreRules

SUPPORTED_FILE_EXTENSIONS: dict[str, SourceLanguage] = {
    ".py": SourceLanguage.PYTHON,
    ".pyi": SourceLanguage.PYTHON,
    ".js": SourceLanguage.JAVASCRIPT,
    ".jsx": SourceLanguage.JAVASCRIPT,
    ".mjs": SourceLanguage.JAVASCRIPT,
    ".cjs": SourceLanguage.JAVASCRIPT,
    ".ts": SourceLanguage.TYPESCRIPT,
    ".tsx": SourceLanguage.TYPESCRIPT,
    ".mts": SourceLanguage.TYPESCRIPT,
    ".cts": SourceLanguage.TYPESCRIPT,
}


@dataclass(frozen=True, slots=True)
class RepositoryScannerConfig:
    """Configuration controlling repository scanning."""

    max_file_size_bytes: int = 1_000_000
    binary_probe_size_bytes: int = 8_192

    def __post_init__(self) -> None:
        if self.max_file_size_bytes <= 0:
            raise ValueError(
                "max_file_size_bytes must be greater than zero",
            )

        if self.binary_probe_size_bytes <= 0:
            raise ValueError(
                "binary_probe_size_bytes must be greater than zero",
            )


class RepositoryScanner:
    """Discover supported source files in a local directory."""

    def __init__(
        self,
        config: RepositoryScannerConfig | None = None,
    ) -> None:
        self._config = config or RepositoryScannerConfig()

    def scan(
        self,
        repository_path: str | Path,
    ) -> RepositoryScanResult:
        """Scan one repository and return immutable metadata."""

        repository_root = Path(repository_path).expanduser().resolve()

        self._validate_repository_path(repository_root)

        ignore_rules = IgnoreRules.from_repository(
            repository_root,
        )

        files: list[ScannedSourceFile] = []

        discovered_file_count = 0
        ignored_file_count = 0
        pruned_directory_count = 0
        unsupported_file_count = 0
        oversized_file_count = 0
        binary_file_count = 0
        symlink_file_count = 0
        inaccessible_file_count = 0

        try:
            for (
                directory_path,
                directory_names,
                file_names,
            ) in repository_root.walk(
                top_down=True,
                on_error=self._raise_traversal_error,
                follow_symlinks=False,
            ):
                retained_directories: list[str] = []

                for directory_name in directory_names:
                    child_path = directory_path / directory_name
                    relative_directory = PurePosixPath(
                        child_path.relative_to(repository_root).as_posix(),
                    )

                    if ignore_rules.should_prune_directory(
                        directory_name=directory_name,
                        directory_path=child_path,
                        relative_path=relative_directory,
                    ):
                        pruned_directory_count += 1
                        continue

                    retained_directories.append(
                        directory_name,
                    )

                directory_names[:] = retained_directories

                for file_name in sorted(file_names):
                    discovered_file_count += 1
                    file_path = directory_path / file_name

                    if file_path.is_symlink():
                        symlink_file_count += 1
                        continue

                    relative_path = PurePosixPath(
                        file_path.relative_to(repository_root).as_posix(),
                    )

                    if ignore_rules.matches_gitignore(
                        relative_path,
                    ):
                        ignored_file_count += 1
                        continue

                    language = self._detect_language(
                        file_path,
                    )

                    if language is None:
                        unsupported_file_count += 1
                        continue

                    try:
                        file_size = file_path.stat().st_size

                        if file_size > self._config.max_file_size_bytes:
                            oversized_file_count += 1
                            continue

                        if self._is_binary_file(file_path):
                            binary_file_count += 1
                            continue

                        content_hash = self._calculate_hash(
                            file_path,
                        )
                    except OSError:
                        inaccessible_file_count += 1
                        continue

                    files.append(
                        ScannedSourceFile(
                            repository_root=repository_root,
                            relative_path=relative_path,
                            language=language,
                            size_bytes=file_size,
                            content_hash=content_hash,
                        ),
                    )
        except RepositoryTraversalError:
            raise
        except OSError as exc:
            raise RepositoryTraversalError(
                repository_root,
                str(exc),
            ) from exc

        files.sort(
            key=lambda source_file: source_file.relative_path.as_posix(),
        )

        statistics = RepositoryScanStatistics(
            discovered_file_count=discovered_file_count,
            included_file_count=len(files),
            ignored_file_count=ignored_file_count,
            pruned_directory_count=pruned_directory_count,
            unsupported_file_count=unsupported_file_count,
            oversized_file_count=oversized_file_count,
            binary_file_count=binary_file_count,
            symlink_file_count=symlink_file_count,
            inaccessible_file_count=inaccessible_file_count,
        )

        return RepositoryScanResult(
            repository_root=repository_root,
            files=tuple(files),
            statistics=statistics,
        )

    @staticmethod
    def _validate_repository_path(
        repository_root: Path,
    ) -> None:
        if not repository_root.exists():
            raise RepositoryNotFoundError(
                repository_root,
            )

        if not repository_root.is_dir():
            raise InvalidRepositoryPathError(
                repository_root,
            )

    @staticmethod
    def _detect_language(
        file_path: Path,
    ) -> SourceLanguage | None:
        return SUPPORTED_FILE_EXTENSIONS.get(
            file_path.suffix.lower(),
        )

    def _is_binary_file(
        self,
        file_path: Path,
    ) -> bool:
        with file_path.open("rb") as source_file:
            sample = source_file.read(
                self._config.binary_probe_size_bytes,
            )

        return b"\x00" in sample

    @staticmethod
    def _calculate_hash(
        file_path: Path,
    ) -> str:
        with file_path.open("rb") as source_file:
            digest = hashlib.file_digest(
                source_file,
                "sha256",
            )

        return digest.hexdigest()

    @staticmethod
    def _raise_traversal_error(
        error: OSError,
    ) -> None:
        error_path = Path(error.filename) if error.filename else Path(".")

        raise RepositoryTraversalError(
            error_path,
            str(error),
        ) from error
