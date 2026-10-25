"""Service for managing repository profiles and sub-project profiles in PostgreSQL."""

from datetime import datetime, timezone
import logging
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.project import Project
from app.model.repo_profile import RepoProfile
from app.model.subrepo_profile import SubrepoProfile
from app.model.repository import Repository
from app.repository_manager.github_url import GitHubUrlParser
from app.repository_manager.resolver import resolve_repository_installation_id
from app.repository_manager_v2 import RepoManagerV2
from app.repository_manager_v2.profile_extractor import RepoProfileService

logger = logging.getLogger(__name__)


class RepoProfileDatabaseService:
    """Service handling repository profile extraction and persistence in PostgreSQL."""

    def __init__(self, repo_manager: RepoManagerV2 | None = None) -> None:
        """Initializes the database profile service.

        Args:
            repo_manager (RepoManagerV2 | None, optional): Manager for GitHub operations.
        """
        self._repo_manager = repo_manager or RepoManagerV2()
        self._extractor_service = RepoProfileService()

    async def get_profile(
        self,
        db: AsyncSession,
        repository_id: int,
    ) -> RepoProfile | None:
        """Retrieves the stored profile for a repository with its sub-project profiles.

        Args:
            db (AsyncSession): Database session.
            repository_id (int): Repository ID.

        Returns:
            RepoProfile | None: Existing profile or None.
        """
        stmt = (
            select(RepoProfile)
            .options(selectinload(RepoProfile.subrepo_profiles))
            .where(RepoProfile.repository_id == repository_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def extract_and_save_profile(
        self,
        db: AsyncSession,
        repository_id: int,
        branch_name: str | None = None,
        force_refresh: bool = False,
        workspace_id: int | None = None,
        destination_override: Path | None = None,
    ) -> RepoProfile:
        """Extracts repository profile (1-shot API + local subprojects) and upserts into database.

        Args:
            db (AsyncSession): Active database session.
            repository_id (int): Target repository ID.
            branch_name (str | None, optional): Specific branch to profile. Defaults to None.
            force_refresh (bool, optional): Force re-extraction. Defaults to False.
            workspace_id (int | None, optional): Workspace ID context. Defaults to None.
            destination_override (Path | None, optional): Local directory override. Defaults to None.

        Returns:
            RepoProfile: Stored or updated RepoProfile instance with sub-project profiles.

        Raises:
            HTTPException: If repository is not found or GitHub API access fails.
        """
        # 1. Fetch Repository
        stmt = (
            select(Repository)
            .options(
                selectinload(Repository.profile).selectinload(
                    RepoProfile.subrepo_profiles
                ),
                selectinload(Repository.branches),
            )
            .where(Repository.id == repository_id)
        )
        res = await db.execute(stmt)
        repo = res.scalar_one_or_none()
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found.",
            )

        # 2. Parse GitHub owner and repo name
        try:
            parsed_url = GitHubUrlParser.parse(repo.git_url)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid GitHub URL for repository {repo.name}: {exc}",
            ) from exc

        # 3. Resolve installation ID for authenticated access
        installation_id = await resolve_repository_installation_id(
            db=db,
            repo=repo,
            workspace_id=workspace_id,
        )

        # 4. Determine target branch
        target_branch = branch_name
        matching_branch = None
        if not target_branch:
            if repo.branches:
                matching_branch = repo.branches[0]
                target_branch = matching_branch.branch_name
            else:
                details = self._repo_manager.get_repo_details(
                    parsed_url.owner,
                    parsed_url.repository,
                    token_or_installation_id=installation_id,
                )
                target_branch = details.get("default_branch", "main")
        else:
            for b in repo.branches:
                if b.branch_name == target_branch:
                    matching_branch = b
                    break

        latest_sha = (
            self._repo_manager.get_branch_commit_sha(
                parsed_url.owner,
                parsed_url.repository,
                target_branch,
                token_or_installation_id=installation_id,
            )
            or "HEAD"
        )

        # 5. Check if cached profile is up-to-date
        existing_profile: RepoProfile | None = repo.profile
        if (
            not force_refresh
            and existing_profile
            and latest_sha != "HEAD"
            and existing_profile.commit_sha == latest_sha
            and existing_profile.branch_name == target_branch
            and existing_profile.subrepo_profiles
        ):
            logger.info(
                "Profile for repository %s is up-to-date. Returning cached.", repo.name
            )
            return existing_profile

        # 6. Fetch 1-shot API metadata
        details = self._repo_manager.get_repo_details(
            parsed_url.owner,
            parsed_url.repository,
            token_or_installation_id=installation_id,
        )
        languages = self._repo_manager.get_repo_languages(
            parsed_url.owner,
            parsed_url.repository,
            token_or_installation_id=installation_id,
        )
        total_lang_bytes = sum(languages.values())
        languages_breakdown: dict[str, float] = {}
        if total_lang_bytes > 0:
            languages_breakdown = {
                k: round((v / total_lang_bytes) * 100, 2) for k, v in languages.items()
            }

        license_name: str | None = None
        raw_license = details.get("license")
        if isinstance(raw_license, dict):
            license_name = raw_license.get("name")

        # 7. Query user-configured Sub-projects (Project records)
        matching_branch_id = matching_branch.id if matching_branch else None
        projects: list[Project] = []
        if matching_branch_id is not None:
            proj_stmt = select(Project).where(
                Project.branch_id == matching_branch_id,
                (Project.workspace_id == workspace_id)
                | (Project.workspace_id.is_(None)),
            )
            projects = list((await db.execute(proj_stmt)).scalars().all())

        # Determine local clone path if available
        local_destination = destination_override
        if not local_destination and matching_branch and matching_branch.local_path:
            p = Path(matching_branch.local_path)
            if p.exists():
                local_destination = p

        readme_summary, readme_content = self._extractor_service.extract_readme_summary(
            local_destination
        )
        summary = details.get("description") or readme_summary

        # 8. Upsert RepoProfile
        if existing_profile is not None:
            existing_profile.branch_id = matching_branch_id
            existing_profile.branch_name = target_branch
            existing_profile.commit_sha = latest_sha
            existing_profile.primary_language = str(
                details.get("language", "unknown")
            ).lower()
            existing_profile.summary = summary
            existing_profile.readme_content = readme_content
            existing_profile.license_name = license_name
            existing_profile.topics = list(details.get("topics", []))
            existing_profile.languages_breakdown = languages_breakdown
            existing_profile.analyzed_at = datetime.now(timezone.utc)
            profile_record = existing_profile
        else:
            profile_record = RepoProfile(
                repository_id=repo.id,
                branch_id=matching_branch_id,
                branch_name=target_branch,
                commit_sha=latest_sha,
                primary_language=str(details.get("language", "unknown")).lower(),
                summary=summary,
                readme_content=readme_content,
                license_name=license_name,
                topics=list(details.get("topics", [])),
                languages_breakdown=languages_breakdown,
            )
            db.add(profile_record)
            await db.flush()

        # 9. Extract and Upsert SubrepoProfile for each user-configured Project
        if local_destination and projects:
            # Delete old subrepo profiles for this repo_profile to ensure clean state
            await db.execute(
                delete(SubrepoProfile).where(
                    SubrepoProfile.repo_profile_id == profile_record.id
                )
            )

            for proj in projects:
                proj_path = local_destination / proj.root_dir.lstrip("./")
                lang_str = (
                    proj.language.value
                    if hasattr(proj.language, "value")
                    else str(proj.language)
                )
                sub_res = self._extractor_service.extract_subproject(
                    local_dir=proj_path,
                    language=lang_str,
                    name=proj.root_dir,
                    root_dir=proj.root_dir,
                )

                subrepo = SubrepoProfile(
                    repo_profile_id=profile_record.id,
                    project_id=proj.id,
                    name=sub_res.name,
                    root_dir=sub_res.root_dir,
                    language=sub_res.language,
                    project_type=sub_res.project_type,
                    frameworks=sub_res.frameworks,
                    tech_stack=sub_res.tech_stack,
                    key_entrypoints=sub_res.key_entrypoints,
                    directory_map=sub_res.directory_map,
                    extra_info=sub_res.extra_info,
                )
                db.add(subrepo)

        await db.commit()

        # Reload with relationships
        stmt_reload = (
            select(RepoProfile)
            .options(selectinload(RepoProfile.subrepo_profiles))
            .where(RepoProfile.id == profile_record.id)
        )
        profile_loaded = (await db.execute(stmt_reload)).scalar_one()

        logger.info(
            "Successfully extracted and saved profile for %s with %d subrepos",
            repo.name,
            len(profile_loaded.subrepo_profiles),
        )
        return profile_loaded
