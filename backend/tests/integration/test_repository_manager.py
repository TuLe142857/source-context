"""Integration tests for local repository management."""

import subprocess
from pathlib import Path

from app.core.config import Settings
from app.domain.repository import (
    RepositoryAcquisitionStatus,
    RepositorySourceType,
)
from app.repository_manager import RepositoryManager


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
