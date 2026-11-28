"""Base source file provider interface.

Defines the contract for reading repository contents from different sources
(e.g., local cloned disk directory or remote GitHub API).
"""

from collections.abc import Sequence
from typing import Any, Protocol


class SourceFileProvider(Protocol):
    """Protocol defining file reading and inspection operations."""

    def exists(self, relative_path: str) -> bool:
        """Checks if a file or directory exists at the relative path.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            bool: True if the path exists, False otherwise.
        """
        ...

    def is_file(self, relative_path: str) -> bool:
        """Checks if the path is an existing regular file.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            bool: True if it is a regular file, False otherwise.
        """
        ...

    def is_dir(self, relative_path: str) -> bool:
        """Checks if the path is an existing directory.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            bool: True if it is a directory, False otherwise.
        """
        ...

    def read_text(self, relative_path: str) -> str | None:
        """Reads file content as a UTF-8 string.

        Args:
            relative_path (str): Relative path from the repository root.

        Returns:
            str | None: Decoded text content or None if file cannot be read.
        """
        ...

    def list_dir(self, relative_path: str = "") -> Sequence[str]:
        """Lists file and directory names directly inside a directory.

        Args:
            relative_path (str, optional): Relative directory path. Defaults to root ("").

        Returns:
            Sequence[str]: List of entry names (not full paths).
        """
        ...

    def find_files(self, pattern: str, max_depth: int = 3) -> Sequence[str]:
        """Finds relative file paths matching a simple name pattern up to a maximum depth.

        Args:
            pattern (str): File name pattern or exact name (e.g. "pyproject.toml").
            max_depth (int, optional): Maximum directory depth to search. Defaults to 3.

        Returns:
            Sequence[str]: List of matching relative paths.
        """
        ...

    def get_all_files(self) -> Sequence[str]:
        """Returns all relative regular file paths available in the repository.

        Excludes internal version control folders (.git) and virtualenvs.

        Returns:
            Sequence[str]: Complete list of relative file paths.
        """
        ...

    def get_api_metadata(self) -> dict[str, Any]:
        """Returns authoritative API metadata if available (e.g. from GitHub API).

        Returns:
            dict[str, Any]: Dictionary containing topics, language, license, and stats.
        """
        ...
