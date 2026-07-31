"""Managed filesystem workspace for cloned repositories."""

from dataclasses import dataclass
from pathlib import Path

from app.repository_manager.exceptions import RepositoryWorkspaceError
from app.repository_manager.github_url import GitHubRepositoryReference


@dataclass(frozen=True, slots=True)
class RepositoryWorkspace:
    """Manage deterministic destinations for cloned repositories."""

    root: Path

    def __post_init__(self) -> None:
        resolved_root = self.root.expanduser().resolve()
        resolved_root.mkdir(parents=True, exist_ok=True)

        if not resolved_root.is_dir():
            raise RepositoryWorkspaceError(
                f"Repository workspace is not a directory: {resolved_root}",
            )

        object.__setattr__(self, "root", resolved_root)

    def destination_for(
        self,
        reference: GitHubRepositoryReference,
    ) -> Path:
        """Return a safe destination for a GitHub repository."""

        destination = (self.root / reference.workspace_directory_name).resolve()

        if not destination.is_relative_to(self.root):
            raise RepositoryWorkspaceError(
                "Resolved repository destination escaped workspace root.",
            )

        return destination
