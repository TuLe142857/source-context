"""Service for managing repository profiles and triggering API-based extraction."""

from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.repo_profile import RepoProfile
from app.model.repository import Repository
from app.repository_manager.github_url import GitHubUrlParser
from app.repository_manager.resolver import resolve_repository_installation_id
from app.repository_manager_v2 import RepoManagerV2

logger = logging.getLogger(__name__)


class RepoProfileDatabaseService:
    """Service handling repository profile extraction and persistence in PostgreSQL."""

    def __init__(self, repo_manager: RepoManagerV2 | None = None) -> None:
        """Initializes the database profile service.

        Args:
            repo_manager (RepoManagerV2 | None, optional): Manager for GitHub operations.
        """
        self._repo_manager = repo_manager or RepoManagerV2()

    async def get_profile(
        self,
        db: AsyncSession,
        repository_id: int,
    ) -> RepoProfile | None:
        """Retrieves the stored profile for a repository.

        Args:
            db (AsyncSession): Database session.
            repository_id (int): Repository ID.

        Returns:
            RepoProfile | None: Existing profile or None.
        """
        stmt = select(RepoProfile).where(RepoProfile.repository_id == repository_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def extract_and_save_profile(
        self,
        db: AsyncSession,
        repository_id: int,
        branch_name: str | None = None,
        force_refresh: bool = False,
        workspace_id: int | None = None,
    ) -> RepoProfile:
        """Extracts repository profile via GitHub API (Zero-Clone) and upserts into database.

        Args:
            db (AsyncSession): Active database session.
            repository_id (int): Target repository ID.
            branch_name (str | None, optional): Specific branch to profile. Defaults to None.
            force_refresh (bool, optional): Force re-extraction. Defaults to False.
            workspace_id (int | None, optional): Workspace ID context. Defaults to None.

        Returns:
            RepoProfile: Stored or updated RepoProfile instance.

        Raises:
            HTTPException: If repository is not found or GitHub API access fails.
        """
        # 1. Fetch Repository
        stmt = (
            select(Repository)
            .options(
                selectinload(Repository.profile),
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

        # 4. Determine target branch and check cache
        existing_profile: RepoProfile | None = repo.profile
        target_branch = branch_name
        if not target_branch:
            if repo.branches:
                target_branch = repo.branches[0].branch_name
            else:
                details = self._repo_manager.get_repo_details(
                    parsed_url.owner,
                    parsed_url.repository,
                    token_or_installation_id=installation_id,
                )
                target_branch = details.get("default_branch", "main")

        # 5. Check if cached profile is up-to-date
        latest_sha = self._repo_manager.get_branch_commit_sha(
            parsed_url.owner,
            parsed_url.repository,
            target_branch,
            token_or_installation_id=installation_id,
        )

        if (
            not force_refresh
            and existing_profile
            and latest_sha
            and existing_profile.commit_sha == latest_sha
            and existing_profile.branch_name == target_branch
        ):
            logger.info(
                "Profile for repository %s is up-to-date (commit: %s). Returning cached.",
                repo.name,
                latest_sha,
            )
            return existing_profile

        # 6. Perform Zero-Clone API profile extraction
        logger.info(
            "Extracting profile for repo %s/%s branch %s via GitHub API (Zero-Clone)...",
            parsed_url.owner,
            parsed_url.repository,
            target_branch,
        )
        extracted = self._repo_manager.get_repo_profile(
            owner=parsed_url.owner,
            repo=parsed_url.repository,
            branch=target_branch,
            installation_id=installation_id,
        )

        # 7. Match branch in database if registered
        matching_branch_id: int | None = None
        for b in repo.branches:
            if b.branch_name == target_branch:
                matching_branch_id = b.id
                break

        # 8. Upsert RepoProfile record
        commit_sha_val = extracted.commit_sha or latest_sha or "HEAD"

        if existing_profile is not None:
            existing_profile.branch_id = matching_branch_id
            existing_profile.branch_name = target_branch
            existing_profile.commit_sha = commit_sha_val
            existing_profile.primary_language = extracted.primary_language
            existing_profile.project_type = extracted.project_type
            existing_profile.summary = extracted.summary
            existing_profile.tech_stack = extracted.tech_stack.model_dump()
            existing_profile.dev_commands = extracted.dev_commands.model_dump()
            existing_profile.coding_conventions = (
                extracted.coding_conventions.model_dump()
            )
            existing_profile.key_entrypoints = extracted.key_entrypoints
            existing_profile.directory_map = extracted.directory_map
            existing_profile.metrics = extracted.metrics.model_dump()
            existing_profile.extra_info = extracted.extra_info
            existing_profile.analyzed_at = datetime.now(timezone.utc)
            profile_record = existing_profile
        else:
            profile_record = RepoProfile(
                repository_id=repo.id,
                branch_id=matching_branch_id,
                branch_name=target_branch,
                commit_sha=commit_sha_val,
                primary_language=extracted.primary_language,
                project_type=extracted.project_type,
                summary=extracted.summary,
                tech_stack=extracted.tech_stack.model_dump(),
                dev_commands=extracted.dev_commands.model_dump(),
                coding_conventions=extracted.coding_conventions.model_dump(),
                key_entrypoints=extracted.key_entrypoints,
                directory_map=extracted.directory_map,
                metrics=extracted.metrics.model_dump(),
                extra_info=extracted.extra_info,
            )
            db.add(profile_record)

        await db.commit()
        await db.refresh(profile_record)

        logger.info(
            "Successfully extracted and saved profile for %s (language=%s, stack=%s)",
            repo.name,
            profile_record.primary_language,
            profile_record.tech_stack.get("frameworks"),
        )
        return profile_record
