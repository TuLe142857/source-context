"""Local filesystem implementation of SourceFileProvider.

Provides file and directory inspection operations for repositories
cloned or downloaded to a local disk path.
"""

from collections.abc import Sequence
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LocalDiskSourceProvider:
    """Source file provider backed by a local disk directory."""

    def __init__(self, root_path: Path) -> None:
        """Initializes the LocalDiskSourceProvider.

        Args:
            root_path (Path): Root directory path of the repository.
        """
        self._root_path = root_path.resolve()
        self._all_files: list[str] | None = None

    @property
    def root_path(self) -> Path:
        """Returns the absolute root directory path."""
        return self._root_path

    def _resolve(self, relative_path: str) -> Path:
        """Safely resolves a relative path within the root directory.

        Args:
            relative_path (str): Relative path string.

        Returns:
            Path: Resolved path.
        """
        clean_path = relative_path.strip("/")
        return self._root_path / clean_path

    def exists(self, relative_path: str) -> bool:
        """Checks if a file or directory exists at the relative path.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            bool: True if the path exists, False otherwise.
        """
        try:
            return self._resolve(relative_path).exists()
        except (OSError, ValueError):
            return False

    def is_file(self, relative_path: str) -> bool:
        """Checks if the path is an existing regular file.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            bool: True if it is a regular file, False otherwise.
        """
        try:
            target = self._resolve(relative_path)
            return target.is_file()
        except (OSError, ValueError):
            return False

    def is_dir(self, relative_path: str) -> bool:
        """Checks if the path is an existing directory.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            bool: True if it is a directory, False otherwise.
        """
        try:
            target = self._resolve(relative_path)
            return target.is_dir()
        except (OSError, ValueError):
            return False

    def read_text(self, relative_path: str) -> str | None:
        """Reads file content as a UTF-8 string.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            str | None: Decoded text content or None if file cannot be read.
        """
        target = self._resolve(relative_path)
        if not target.is_file():
            return None

        try:
            return target.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as exc:
            logger.warning("Failed to read file %s: %s", target, exc)
            return None

    def list_dir(self, relative_path: str = "") -> Sequence[str]:
        """Lists file and directory names directly inside a directory.

        Args:
            relative_path (str, optional): Relative directory path. Defaults to root ("").

        Returns:
            Sequence[str]: List of entry names (excluding .git).
        """
        target = self._resolve(relative_path)
        if not target.is_dir():
            return []

        try:
            return [entry.name for entry in target.iterdir() if entry.name != ".git"]
        except (OSError, PermissionError) as exc:
            logger.warning("Failed to list directory %s: %s", target, exc)
            return []

    def find_files(self, pattern: str, max_depth: int = 3) -> Sequence[str]:
        """Finds relative file paths matching a simple name pattern up to a maximum depth.

        Args:
            pattern (str): File name pattern (e.g. "pyproject.toml" or "*.py").
            max_depth (int, optional): Maximum directory depth to search. Defaults to 3.

        Returns:
            Sequence[str]: List of matching relative paths.
        """
        results: list[str] = []
        try:
            for match in self._root_path.glob(f"**/{pattern}"):
                if ".git" in match.parts:
                    continue
                try:
                    rel = match.relative_to(self._root_path)
                except ValueError:
                    continue
                if len(rel.parts) <= max_depth:
                    results.append(str(rel))
        except (OSError, PermissionError) as exc:
            logger.warning(
                "Error finding files matching %s in %s: %s",
                pattern,
                self._root_path,
                exc,
            )

        return sorted(results)

    def get_all_files(self) -> Sequence[str]:
        """Returns all relative regular file paths available in the repository.

        Excludes internal version control folders (.git) and virtualenvs.

        Returns:
            Sequence[str]: List of relative paths.
        """
        if self._all_files is not None:
            return self._all_files

        results: list[str] = []
        if self._root_path.exists() and self._root_path.is_dir():
            try:
                for file_path in self._root_path.rglob("*"):
                    if not file_path.is_file():
                        continue
                    try:
                        rel = file_path.relative_to(self._root_path)
                    except ValueError:
                        continue

                    # Ignore internal git and common virtualenvs/caches
                    if any(
                        part.startswith(".")
                        or part in ("node_modules", "__pycache__", "venv", ".venv")
                        for part in rel.parts
                    ):
                        continue

                    results.append(str(rel))
            except (OSError, PermissionError) as exc:
                logger.warning("Failed to scan files in %s: %s", self._root_path, exc)

        self._all_files = sorted(results)
        return self._all_files

    def get_api_metadata(self) -> dict[str, Any]:
        """Returns metadata available from local inspection."""
        metadata: dict[str, Any] = {}
        for name in ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"):
            if self.is_file(name):
                content = self.read_text(name)
                if content:
                    first_line = (
                        content.splitlines()[0].strip() if content.splitlines() else ""
                    )
                    if "MIT" in first_line or "MIT" in content[:200]:
                        metadata["license_name"] = "MIT License"
                    elif "Apache" in first_line or "Apache" in content[:200]:
                        metadata["license_name"] = "Apache-2.0"
                    elif "BSD" in first_line or "BSD" in content[:200]:
                        metadata["license_name"] = "BSD License"
                    elif "GPL" in first_line or "GPL" in content[:200]:
                        metadata["license_name"] = "GPL License"
                    else:
                        metadata["license_name"] = first_line[:50] or "Custom"
                break
        return metadata
