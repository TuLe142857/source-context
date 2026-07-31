"""Exceptions raised by repository management components."""

from collections.abc import Sequence
from pathlib import Path


class RepositoryManagerError(Exception):
    """Base exception for repository management failures."""


class RepositoryNotFoundError(RepositoryManagerError):
    """Raised when a local repository path does not exist."""

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path
        super().__init__(
            f"Repository path does not exist: {repository_path}",
        )


class InvalidRepositoryPathError(RepositoryManagerError):
    """Raised when a repository path is not a directory."""

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path
        super().__init__(
            f"Repository path is not a directory: {repository_path}",
        )


class InvalidGitRepositoryError(RepositoryManagerError):
    """Raised when a path is not contained in a Git repository."""

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path
        super().__init__(
            f"Path is not a Git repository: {repository_path}",
        )


class InvalidGitHubUrlError(RepositoryManagerError):
    """Raised when a public GitHub URL is invalid or unsupported."""

    def __init__(self, repository_url: str) -> None:
        self.repository_url = repository_url
        super().__init__(
            f"Invalid public GitHub repository URL: {repository_url}",
        )


class RepositoryWorkspaceError(RepositoryManagerError):
    """Raised when a managed workspace path is invalid."""


class RepositoryDestinationConflictError(RepositoryManagerError):
    """Raised when a clone destination contains different data."""

    def __init__(self, destination: Path) -> None:
        self.destination = destination
        super().__init__(
            f"Repository destination conflicts with existing data: {destination}",
        )


class GitExecutableNotFoundError(RepositoryManagerError):
    """Raised when the Git executable is unavailable."""

    def __init__(self) -> None:
        super().__init__(
            "Git executable was not found in the current PATH.",
        )


class GitCommandTimeoutError(RepositoryManagerError):
    """Raised when a Git command exceeds its timeout."""

    def __init__(
        self,
        command: Sequence[str],
        timeout_seconds: int,
    ) -> None:
        self.command = tuple(command)
        self.timeout_seconds = timeout_seconds

        super().__init__(
            f"Git command timed out after {timeout_seconds} seconds: {' '.join(command)}",
        )


class GitCommandError(RepositoryManagerError):
    """Raised when a Git command exits unsuccessfully."""

    def __init__(
        self,
        command: Sequence[str],
        return_code: int,
        stderr: str,
    ) -> None:
        self.command = tuple(command)
        self.return_code = return_code
        self.stderr = stderr

        super().__init__(
            f"Git command failed with exit code {return_code}: "
            f"{' '.join(command)}. Error: {stderr.strip()}",
        )


class RepositoryTraversalError(RepositoryManagerError):
    """Raised when a repository tree cannot be traversed."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason

        super().__init__(
            f"Unable to traverse repository path {path}: {reason}",
        )
