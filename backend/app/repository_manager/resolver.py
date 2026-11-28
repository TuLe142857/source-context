"""Repository installation resolution module.

Resolves the appropriate GitHub App installation ID for a given repository and workspace
without exposing credentials across users or workspace members.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.member import Member
from app.model.repository import Repository
from app.model.user import User
from app.model.workspace import Workspace
from app.model.workspace_repository import WorkspaceRepository
from app.repository_manager.github_url import GitHubUrlParser
from app.repository_manager_v2 import RepoManagerV2

logger = logging.getLogger(__name__)


async def resolve_repository_installation_id(
    db: AsyncSession,
    repo: Repository,
    workspace_id: int | None = None,
) -> int | None:
    """Resolves the GitHub App installation ID for a specific repository.

    Prioritizes the repository owner (the user who added the repository),
    followed by the workspace owner, workspace members, other linked workspaces,
    and finally queries GitHub directly via App JWT to support multi-repo workspaces
    without leaking installation IDs among workspace members.

    Args:
        db (AsyncSession): Active asynchronous database session.
        repo (Repository): Target repository model.
        workspace_id (int | None, optional): Contextual workspace ID. Defaults to None.

    Returns:
        int | None: Resolved GitHub App installation ID, or None if unavailable.
    """
    # 1. Check the repository owner (user who registered/added this repository)
    if repo.added_by_user_id:
        user_stmt = select(User).where(User.id == repo.added_by_user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if user and user.github_installation_id:
            logger.debug(
                "Resolved installation_id %s from repo owner (user_id=%d) for repo %s",
                user.github_installation_id,
                repo.added_by_user_id,
                repo.name,
            )
            return user.github_installation_id

    # 2. Check the workspace owner
    if workspace_id:
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws = (await db.execute(ws_stmt)).scalar_one_or_none()
        if ws and ws.owner_id:
            owner_stmt = select(User).where(User.id == ws.owner_id)
            owner = (await db.execute(owner_stmt)).scalar_one_or_none()
            if owner and owner.github_installation_id:
                logger.debug(
                    "Resolved installation_id %s from workspace owner (user_id=%d) for repo %s",
                    owner.github_installation_id,
                    ws.owner_id,
                    repo.name,
                )
                return owner.github_installation_id

    # 3. Check other members in the workspace who have an active GitHub App installation
    if workspace_id:
        member_users_stmt = (
            select(User)
            .join(Member, Member.user_id == User.id)
            .where(
                Member.workspace_id == workspace_id,
                User.github_installation_id.is_not(None),
            )
        )
        members = (await db.execute(member_users_stmt)).scalars().all()
        for m_user in members:
            if m_user.github_installation_id:
                logger.debug(
                    "Resolved installation_id %s from workspace member (user_id=%d) for repo %s",
                    m_user.github_installation_id,
                    m_user.id,
                    repo.name,
                )
                return m_user.github_installation_id

    # 4. Check other workspaces linked to this repository
    ws_repo_stmt = (
        select(User)
        .join(Workspace, Workspace.owner_id == User.id)
        .join(WorkspaceRepository, WorkspaceRepository.workspace_id == Workspace.id)
        .where(
            WorkspaceRepository.repository_id == repo.id,
            User.github_installation_id.is_not(None),
        )
    )
    linked_owners = (await db.execute(ws_repo_stmt)).scalars().all()
    for l_user in linked_owners:
        if l_user.github_installation_id:
            logger.debug(
                "Resolved installation_id %s from linked workspace owner (user_id=%d) for repo %s",
                l_user.github_installation_id,
                l_user.id,
                repo.name,
            )
            return l_user.github_installation_id

    # 5. Direct GitHub App installation lookup via App JWT
    try:
        ref = GitHubUrlParser.parse(repo.git_url)
        manager = RepoManagerV2()
        gh_inst_id = manager.get_repo_installation_id(ref.owner, ref.repository)
        if gh_inst_id:
            logger.debug(
                "Resolved installation_id %s dynamically from GitHub App for %s/%s",
                gh_inst_id,
                ref.owner,
                ref.repository,
            )
            return gh_inst_id
    except Exception as exc:
        logger.debug(
            "Dynamic GitHub App installation lookup failed for %s: %s",
            repo.git_url,
            exc,
        )

    return None
