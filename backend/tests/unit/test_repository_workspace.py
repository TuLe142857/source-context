"""Tests for the managed repository workspace."""

from pathlib import Path

from app.repository_manager.github_url import (
    GitHubRepositoryReference,
)
from app.repository_manager.workspace import RepositoryWorkspace


def test_workspace_builds_deterministic_destination(
    tmp_path: Path,
) -> None:
    """GitHub repositories should receive deterministic folders."""

    workspace = RepositoryWorkspace(
        tmp_path / "repositories",
    )

    reference = GitHubRepositoryReference(
        owner="Encode",
        repository="HTTPX",
    )

    destination = workspace.destination_for(
        reference,
    )

    assert destination == (workspace.root / "github__encode__httpx")
    assert destination.is_relative_to(
        workspace.root,
    )
