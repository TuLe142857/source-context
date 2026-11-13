"""Integration tests for local repository management."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.repository_manager import RepositoryManager
from app.repository_manager_v2.manager import RepoManagerV2
from app.schemas.repository import (
    RepositoryAcquisitionStatus,
    RepositorySourceType,
)


def run_git(
    repository_path: Path,
    *arguments: str,
) -> None:
    """Run a Git command in the temporary test repository."""

    subprocess.run(
        [
            "git",
            "-C",
            str(repository_path),
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_manager_scans_local_git_repository(
    tmp_path: Path,
) -> None:
    """A local path should resolve to its Git root and snapshot."""

    repository_path = tmp_path / "local-repository"
    repository_path.mkdir()

    subprocess.run(
        [
            "git",
            "init",
            str(repository_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    source_directory = repository_path / "app"
    source_directory.mkdir()

    (source_directory / "service.py").write_text(
        "def execute() -> None:\n    pass\n",
        encoding="utf-8",
    )

    run_git(repository_path, "add", ".")
    run_git(
        repository_path,
        "-c",
        "user.name=Source Context Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "Initial commit",
    )

    settings = Settings(
        repository_workspace_root=(tmp_path / "workspace"),
        scanner_max_file_size_bytes=1_000_000,
        git_command_timeout_seconds=30,
    )

    manager = RepositoryManager.from_settings(
        settings,
    )

    snapshot = manager.scan_local(
        source_directory,
    )

    assert snapshot.repository.source_type is RepositorySourceType.LOCAL
    assert snapshot.repository.acquisition_status is RepositoryAcquisitionStatus.LOCAL
    assert snapshot.repository.local_path == repository_path.resolve()
    assert snapshot.git.commit_sha
    assert snapshot.statistics.included_file_count == 1
    assert snapshot.files[0].relative_path.as_posix() == "app/service.py"


def test_repo_manager_compares_commit_changes_nul_safely(tmp_path: Path) -> None:
    repository_path = tmp_path / "diff-repository"
    repository_path.mkdir()
    subprocess.run(["git", "init", str(repository_path)], check=True, capture_output=True)
    (repository_path / "old name.py").write_text("value = 1\n", encoding="utf-8")
    run_git(repository_path, "add", ".")
    run_git(
        repository_path,
        "-c", "user.name=Source Context Test",
        "-c", "user.email=test@example.com",
        "commit", "-m", "initial",
    )
    base_sha = subprocess.run(
        ["git", "-C", str(repository_path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    (repository_path / "old name.py").rename(repository_path / "new 名.py")
    (repository_path / "added file.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repository_path, "add", ".")
    run_git(
        repository_path,
        "-c", "user.name=Source Context Test",
        "-c", "user.email=test@example.com",
        "commit", "-m", "rename and add",
    )
    target_sha = subprocess.run(
        ["git", "-C", str(repository_path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    changes = RepoManagerV2().compare_commits(repository_path, base_sha, target_sha)

    assert changes.renamed == (("old name.py", "new 名.py"),)
    assert changes.added == ("added file.py",)


def test_clone_update_does_not_report_head_when_fetch_fails(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    manager = RepoManagerV2()
    manager._run_git = Mock(side_effect=RuntimeError("fetch failed"))  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="fetch failed"):
        manager.clone_or_update_branch("https://example.invalid/repo.git", "main", checkout)

    assert manager._run_git.call_count == 1  # type: ignore[union-attr]
