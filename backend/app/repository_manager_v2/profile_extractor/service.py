"""Repository profile extraction orchestrator service.

Acts as a Facade coordinating SourceFileProvider and ExtractorRegistry
to produce comprehensive technical profiles of repositories.
"""

from collections.abc import Sequence
import logging
from pathlib import Path
from typing import Any

from app.repository_manager_v2.profile_extractor.extractors.registry import (
    ExtractorRegistry,
    get_default_extractor_registry,
)
from app.repository_manager_v2.profile_extractor.models import (
    MetricsInfo,
    RepoProfileResult,
)
from app.repository_manager_v2.profile_extractor.providers.base import (
    SourceFileProvider,
)
from app.repository_manager_v2.profile_extractor.providers.local import (
    LocalDiskSourceProvider,
)

logger = logging.getLogger(__name__)


class RepoProfileService:
    """Orchestrator service for profiling repositories."""

    def __init__(
        self,
        registry: ExtractorRegistry | None = None,
    ) -> None:
        """Initializes the service with an optional custom registry.

        Args:
            registry (ExtractorRegistry | None, optional): Extractor registry to use.
                Defaults to get_default_extractor_registry().
        """
        self._registry = registry or get_default_extractor_registry()

    def profile_provider(
        self,
        provider: SourceFileProvider,
        repository_url: str | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> RepoProfileResult:
        """Profiles a repository using an abstract SourceFileProvider.

        Args:
            provider (SourceFileProvider): File inspection provider.
            repository_url (str | None, optional): Git clone URL. Defaults to None.
            branch_name (str | None, optional): Branch name. Defaults to None.
            commit_sha (str | None, optional): Commit hash. Defaults to None.
            extra_info (dict[str, Any] | None, optional): Extra metadata. Defaults to None.

        Returns:
            RepoProfileResult: Aggregated technical profile.
        """
        extractors = self._registry.get_extractors_for_repo(provider)

        if not extractors:
            logger.info("No language extractors matched repository files.")
            result = RepoProfileResult(
                repository_url=repository_url,
                branch_name=branch_name,
                commit_sha=commit_sha,
                extra_info=extra_info or {},
            )
            self._fill_generic_metrics(provider, result.metrics)
            return result

        # Run the primary matching extractor
        primary_extractor = extractors[0]
        result = primary_extractor.extract(provider)
        result.repository_url = repository_url
        result.branch_name = branch_name
        result.commit_sha = commit_sha
        if extra_info:
            result.extra_info.update(extra_info)

        self._fill_generic_metrics(provider, result.metrics)
        return result

    def profile_directory(
        self,
        destination: Path,
        repository_url: str | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> RepoProfileResult:
        """Convenience method to profile a local cloned directory.

        Args:
            destination (Path): Directory path on disk.
            repository_url (str | None, optional): Git clone URL. Defaults to None.
            branch_name (str | None, optional): Branch name. Defaults to None.
            commit_sha (str | None, optional): Commit hash. Defaults to None.
            extra_info (dict[str, Any] | None, optional): Extra metadata. Defaults to None.

        Returns:
            RepoProfileResult: Aggregated technical profile.
        """
        provider = LocalDiskSourceProvider(destination)
        result = self.profile_provider(
            provider=provider,
            repository_url=repository_url,
            branch_name=branch_name,
            commit_sha=commit_sha,
            extra_info=extra_info,
        )

        # Count total files on local disk accurately
        if destination.exists() and destination.is_dir():
            try:
                result.metrics.total_files = len(
                    [
                        f
                        for f in destination.rglob("*")
                        if f.is_file() and ".git" not in f.parts
                    ]
                )
            except (OSError, PermissionError) as exc:
                logger.warning("Failed to count files in %s: %s", destination, exc)

        return result

    def profile_github_repository(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        token: str | None = None,
        commit_sha: str | None = None,
        summary: str | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> RepoProfileResult:
        """Profiles a remote GitHub repository via API without cloning (Zero-Clone).

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            branch (str, optional): Target branch. Defaults to "main".
            token (str | None, optional): GitHub access token. Defaults to None.
            commit_sha (str | None, optional): Specific commit SHA if known. Defaults to None.
            summary (str | None, optional): Repository summary / description. Defaults to None.
            extra_info (dict[str, Any] | None, optional): Extra metadata. Defaults to None.

        Returns:
            RepoProfileResult: Aggregated technical profile extracted via GitHub API.
        """
        from app.repository_manager_v2.profile_extractor.providers.github import (
            GitHubApiSourceProvider,
        )

        provider = GitHubApiSourceProvider(
            owner=owner,
            repo=repo,
            branch=branch,
            token=token,
        )
        repo_url = f"https://github.com/{owner}/{repo}.git"

        result = self.profile_provider(
            provider=provider,
            repository_url=repo_url,
            branch_name=branch,
            commit_sha=commit_sha,
            extra_info=extra_info,
        )

        # Total files can be directly retrieved from indexed blobs in the Git tree
        result.metrics.total_files = len(provider._blobs)

        if summary:
            result.summary = summary
        elif not result.summary and result.metrics.readme_file:
            readme_text = provider.read_text(result.metrics.readme_file)
            if readme_text:
                result.summary = self._extract_summary_from_readme(readme_text)

        return result

    @staticmethod
    def _extract_summary_from_readme(readme_text: str) -> str | None:
        """Extracts first informative paragraph from README markdown."""
        lines = [line.strip() for line in readme_text.splitlines()]
        paragraphs: list[str] = []
        current: list[str] = []

        for line in lines:
            if not line:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
            elif not line.startswith(("#", "[!", "<!--", "```", "![", "<img")):
                current.append(line)

        if current:
            paragraphs.append(" ".join(current))

        for para in paragraphs:
            if len(para) > 20:
                return para[:500]

        return None

    def _fill_generic_metrics(
        self,
        provider: SourceFileProvider,
        metrics: MetricsInfo,
    ) -> None:
        """Fills common metrics like README detection."""
        root_entries: Sequence[str] = provider.list_dir("")
        for name in root_entries:
            if name.lower().startswith("readme") and not metrics.has_readme:
                metrics.has_readme = True
                metrics.readme_file = name
                break
