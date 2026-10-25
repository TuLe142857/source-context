"""Repository and sub-repository profile extraction service."""

import logging
from pathlib import Path
import re
from typing import Any

from app.repository_manager_v2.profile_extractor.extractors.registry import (
    SubprojectExtractorRegistry,
    get_default_subproject_registry,
)
from app.repository_manager_v2.profile_extractor.extractor import (
    extract_subproject_profile,
)
from app.repository_manager_v2.profile_extractor.models import (
    RepoProfileResult,
    SubrepoProfileResult,
)

logger = logging.getLogger(__name__)


class RepoProfileService:
    """Orchestrator service for profiling repositories and their sub-projects."""

    def __init__(
        self,
        registry: SubprojectExtractorRegistry | None = None,
    ) -> None:
        """Initializes service with optional subproject extractor registry."""
        self._registry = registry or get_default_subproject_registry()

    def extract_subproject(
        self,
        local_dir: Path,
        language: str,
        name: str = "",
        root_dir: str = ".",
    ) -> SubrepoProfileResult:
        """Extracts technical profile for a configured sub-project from local disk.

        Args:
            local_dir (Path): Subproject root directory.
            language (str): Configured language of the subproject.
            name (str, optional): Name of the subproject. Defaults to "".
            root_dir (str, optional): Relative directory inside repository. Defaults to ".".

        Returns:
            SubrepoProfileResult: Extracted sub-repository profile.
        """
        return extract_subproject_profile(
            local_dir=local_dir,
            language=language,
            name=name,
            root_dir=root_dir,
            registry=self._registry,
        )

    def extract_readme_summary(
        self, destination: Path | None
    ) -> tuple[str | None, str | None]:
        """Extracts content snippet and short summary from root README.

        Args:
            destination (Path | None): Local repository directory.

        Returns:
            tuple[str | None, str | None]: (summary, readme_content).
        """
        if not destination or not destination.exists():
            return None, None

        for readme_name in ("README.md", "README", "readme.markdown", "Readme.md"):
            readme_path = destination / readme_name
            if readme_path.exists() and readme_path.is_file():
                try:
                    content = readme_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).strip()
                    if not content:
                        continue

                    # Extract first non-header paragraph as summary
                    summary: str | None = None
                    for paragraph in content.split("\n\n"):
                        p_stripped = paragraph.strip()
                        if (
                            p_stripped
                            and not p_stripped.startswith("#")
                            and not p_stripped.startswith("!")
                        ):
                            clean = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", p_stripped)
                            clean = re.sub(r"[`*_{}]", "", clean)
                            clean = " ".join(clean.split())
                            if len(clean) > 20:
                                summary = clean[:300]
                                break

                    readme_snippet = content[:2000]
                    return summary, readme_snippet
                except Exception as exc:
                    logger.debug("Failed reading README at %s: %s", readme_path, exc)

        return None, None

    def profile_repository(
        self,
        destination: Path | None,
        branch_name: str = "main",
        commit_sha: str = "HEAD",
        repository_url: str | None = None,
        api_metadata: dict[str, Any] | None = None,
        subprojects: list[tuple[str, str, str]] | None = None,
    ) -> RepoProfileResult:
        """Profiles the repository and its configured sub-projects.

        Args:
            destination (Path | None): Local clone destination.
            branch_name (str, optional): Branch name. Defaults to "main".
            commit_sha (str, optional): Commit hash. Defaults to "HEAD".
            repository_url (str | None, optional): Clone URL. Defaults to None.
            api_metadata (dict[str, Any] | None, optional): Authoritative 1-shot API metadata.
            subprojects (list[tuple[str, str, str]] | None, optional):
                List of (name, root_dir, language) subprojects. Defaults to None.

        Returns:
            RepoProfileResult: Aggregated repository profile with sub-project profiles.
        """
        api_meta = api_metadata or {}
        summary = api_meta.get("description")
        topics = list(api_meta.get("topics", []))
        license_name = api_meta.get("license_name")
        languages_breakdown = dict(api_meta.get("languages_breakdown", {}))
        primary_language = str(api_meta.get("primary_language", "unknown")).lower()

        # Extract README if local repository is available
        readme_summary, readme_content = self.extract_readme_summary(destination)
        if not summary and readme_summary:
            summary = readme_summary

        subrepos: list[SubrepoProfileResult] = []
        if destination and subprojects:
            for proj_name, proj_root, proj_lang in subprojects:
                proj_dir = destination / proj_root.lstrip("./")
                subrepo_res = self.extract_subproject(
                    local_dir=proj_dir,
                    language=proj_lang,
                    name=proj_name,
                    root_dir=proj_root,
                )
                subrepos.append(subrepo_res)

        return RepoProfileResult(
            repository_url=repository_url,
            branch_name=branch_name,
            commit_sha=commit_sha,
            primary_language=primary_language,
            summary=summary,
            readme_content=readme_content,
            license_name=license_name,
            topics=topics,
            languages_breakdown=languages_breakdown,
            subrepos=subrepos,
        )

    def profile_directory(
        self,
        destination: Path,
        repository_url: str | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> RepoProfileResult:
        """Profiles a local directory with default root project."""
        default_subproject = ("root", ".", "python")
        return self.profile_repository(
            destination=destination,
            branch_name=branch_name or "main",
            commit_sha=commit_sha or "HEAD",
            repository_url=repository_url,
            subprojects=[default_subproject],
        )

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
        """Profiles a remote GitHub repository via 1-shot API without cloning."""
        from app.repository_manager_v2.manager import RepoManagerV2

        manager = RepoManagerV2()
        details = manager.get_repo_details(owner, repo, token_or_installation_id=token)
        languages = manager.get_repo_languages(
            owner, repo, token_or_installation_id=token
        )
        languages_breakdown: dict[str, float] = {}
        total_bytes = sum(languages.values())
        if total_bytes > 0:
            languages_breakdown = {
                k: round((v / total_bytes) * 100, 2) for k, v in languages.items()
            }

        api_metadata: dict[str, Any] = {
            "description": summary or details.get("description"),
            "topics": details.get("topics", []),
            "license_name": details.get("license", {}).get("name")
            if isinstance(details.get("license"), dict)
            else None,
            "languages_breakdown": languages_breakdown,
            "primary_language": details.get("language", "unknown"),
        }

        return self.profile_repository(
            destination=None,
            branch_name=branch,
            commit_sha=commit_sha or "HEAD",
            repository_url=f"https://github.com/{owner}/{repo}.git",
            api_metadata=api_metadata,
        )
