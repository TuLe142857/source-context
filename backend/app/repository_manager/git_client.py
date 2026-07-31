"""Safe subprocess wrapper for Git repository operations."""

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from app.schemas.repository import GitRepositoryMetadata
from app.repository_manager.exceptions import (
    GitCommandError,
    GitCommandTimeoutError,
    GitExecutableNotFoundError,
    InvalidGitRepositoryError,
    RepositoryDestinationConflictError,
)


class GitClient:
    """Execute the Git commands required by Repository Manager."""

    def __init__(self, timeout_seconds: int = 120) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._timeout_seconds = timeout_seconds

    def clone_public_repository(
        self,
        repository_url: str,
        destination: Path,
    ) -> None:
        """Perform a shallow clone into a new destination."""

        if destination.exists():
            raise RepositoryDestinationConflictError(destination)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            self._run(
                [
                    "clone",
                    "--depth",
                    "1",
                    "--single-branch",
                    repository_url,
                    str(destination),
                ],
            )
        except Exception:
            if destination.exists():
                shutil.rmtree(
                    destination,
                    ignore_errors=True,
                )
            raise

    def clone_or_update_branch(
        self,
        repository_url: str,
        branch_name: str,
        destination: Path,
    ) -> GitRepositoryMetadata:
        """Clone a specific branch into destination, or fetch latest if already present.

        Args:
            repository_url: Git clone URL.
            branch_name: Target branch name (e.g. 'main', 'develop').
            destination: Path where repository branch should be stored.

        Returns:
            GitRepositoryMetadata: Metadata including commit_sha and root path.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not destination.exists():
            try:
                self._run(
                    [
                        "clone",
                        "--depth",
                        "1",
                        "--single-branch",
                        "--branch",
                        branch_name,
                        repository_url,
                        str(destination),
                    ],
                )
            except Exception:
                if destination.exists():
                    shutil.rmtree(destination, ignore_errors=True)
                raise
        else:
            try:
                self._run(
                    [
                        "-C",
                        str(destination),
                        "fetch",
                        "origin",
                        branch_name,
                        "--depth",
                        "1",
                    ],
                    check=False,
                )
                self._run(
                    [
                        "-C",
                        str(destination),
                        "reset",
                        "--hard",
                        f"origin/{branch_name}",
                    ],
                    check=False,
                )
            except Exception:
                pass

        return self.get_metadata(destination)

    def get_repository_root(
        self,
        repository_path: Path,
    ) -> Path:
        """Return the root directory of the containing Git repository."""

        result = self._run(
            [
                "-C",
                str(repository_path),
                "rev-parse",
                "--show-toplevel",
            ],
            check=False,
        )

        if result.returncode != 0:
            raise InvalidGitRepositoryError(repository_path)

        root_text = result.stdout.strip()

        if not root_text:
            raise InvalidGitRepositoryError(repository_path)

        return Path(root_text).resolve()

    def get_metadata(
        self,
        repository_path: Path,
    ) -> GitRepositoryMetadata:
        """Read branch, commit and remote metadata."""

        repository_root = self.get_repository_root(repository_path)

        commit_sha = self._run(
            [
                "-C",
                str(repository_root),
                "rev-parse",
                "HEAD",
            ],
        ).stdout.strip()

        branch_text = self._run(
            [
                "-C",
                str(repository_root),
                "branch",
                "--show-current",
            ],
        ).stdout.strip()

        remote_result = self._run(
            [
                "-C",
                str(repository_root),
                "config",
                "--get",
                "remote.origin.url",
            ],
            check=False,
        )

        remote_url = remote_result.stdout.strip() or None

        return GitRepositoryMetadata(
            repository_root=repository_root,
            branch=branch_text or None,
            commit_sha=commit_sha,
            remote_url=remote_url,
        )

    def _run(
        self,
        arguments: Sequence[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run Git without invoking a command shell."""

        command = ["git", *arguments]

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise GitExecutableNotFoundError() from exc
        except subprocess.TimeoutExpired as exc:
            raise GitCommandTimeoutError(
                command,
                self._timeout_seconds,
            ) from exc

        if check and result.returncode != 0:
            raise GitCommandError(
                command,
                result.returncode,
                result.stderr,
            )

        return result
