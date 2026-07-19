"""Repository Manager orchestration service."""

import hashlib
import re
from pathlib import Path

from app.core.config import Settings
from app.domain.repository import (
    PreparedRepository,
    RepositoryAcquisitionStatus,
    RepositorySnapshot,
    RepositorySourceType,
)
from app.repository_manager.clone import (
    GitHubPublicRepositoryProvider,
)
from app.repository_manager.git_client import GitClient
from app.repository_manager.github_url import GitHubUrlParser
from app.repository_manager.scanner import (
    RepositoryScanner,
    RepositoryScannerConfig,
)
from app.repository_manager.workspace import RepositoryWorkspace


class RepositoryManager:
    """Prepare and scan local or public GitHub repositories."""

    def __init__(
        self,
        *,
        git_client: GitClient,
        scanner: RepositoryScanner,
        github_provider: GitHubPublicRepositoryProvider,
    ) -> None:
        self._git_client = git_client
        self._scanner = scanner
        self._github_provider = github_provider

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
    ) -> "RepositoryManager":
        """Build Repository Manager from application settings."""

        git_client = GitClient(
            timeout_seconds=(settings.git_command_timeout_seconds),
        )

        scanner = RepositoryScanner(
            RepositoryScannerConfig(
                max_file_size_bytes=(settings.scanner_max_file_size_bytes),
            ),
        )

        workspace = RepositoryWorkspace(
            settings.repository_workspace_root,
        )

        github_provider = GitHubPublicRepositoryProvider(
            url_parser=GitHubUrlParser(),
            workspace=workspace,
            git_client=git_client,
        )

        return cls(
            git_client=git_client,
            scanner=scanner,
            github_provider=github_provider,
        )

    def scan_local(
        self,
        repository_path: str | Path,
    ) -> RepositorySnapshot:
        """Prepare and scan an existing local Git repository."""

        input_path = Path(repository_path).expanduser().resolve()

        metadata = self._git_client.get_metadata(
            input_path,
        )

        prepared_repository = PreparedRepository(
            repository_id=self._build_local_repository_id(
                metadata.repository_root,
            ),
            source_type=RepositorySourceType.LOCAL,
            acquisition_status=(RepositoryAcquisitionStatus.LOCAL),
            name=metadata.repository_root.name,
            owner=None,
            local_path=metadata.repository_root,
            remote_url=metadata.remote_url,
        )

        return self._create_snapshot(
            prepared_repository,
        )

    def scan_github_public(
        self,
        repository_url: str,
    ) -> RepositorySnapshot:
        """Clone or reuse and then scan a public GitHub repository."""

        prepared_repository = self._github_provider.prepare(
            repository_url,
        )

        return self._create_snapshot(
            prepared_repository,
        )

    def _create_snapshot(
        self,
        repository: PreparedRepository,
    ) -> RepositorySnapshot:
        metadata = self._git_client.get_metadata(
            repository.local_path,
        )

        scan_result = self._scanner.scan(
            metadata.repository_root,
        )

        return RepositorySnapshot(
            repository=repository,
            git=metadata,
            files=scan_result.files,
            statistics=scan_result.statistics,
        )

    @staticmethod
    def _build_local_repository_id(
        repository_root: Path,
    ) -> str:
        normalized_path = str(
            repository_root.resolve(),
        ).casefold()

        path_digest = hashlib.sha256(
            normalized_path.encode("utf-8"),
        ).hexdigest()[:12]

        repository_slug = (
            re.sub(
                r"[^a-zA-Z0-9_.-]+",
                "-",
                repository_root.name,
            )
            .strip("-")
            .casefold()
        )

        if not repository_slug:
            repository_slug = "repository"

        return f"local__{repository_slug}__{path_digest}"
