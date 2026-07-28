"""Vector search service module handling workspace and branch code retrieval."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.branch import Branch
from app.retrieval.retriever import CodeRetriever, QueryResult

logger = logging.getLogger(__name__)


class VectorService:
    """Service class for semantic vector code search across workspaces and repository branches."""

    def __init__(
        self,
        retriever: CodeRetriever,
        db_session: AsyncSession,
    ) -> None:
        """Initializes VectorService with CodeRetriever and AsyncSession dependencies.

        Args:
            retriever (CodeRetriever): CodeRetriever instance.
            db_session (AsyncSession): Database session.
        """
        self.retriever = retriever
        self.db_session = db_session

    async def search(
        self,
        workspace_id: int,
        query: str,
        top_k: int = 5,
    ) -> list[QueryResult]:
        """Performs semantic code search limited to a specific workspace.

        Args:
            workspace_id (int): Target workspace ID.
            query (str): Natural language search prompt.
            top_k (int, optional): Maximum number of hits to return (defaults to 5).

        Returns:
            list[QueryResult]: Ranked list of search result hits.
        """
        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            workspace_id=workspace_id,
        )

    async def search_with_branch_filter(
        self,
        repository_id: int,
        branch_name: str,
        query: str,
        top_k: int = 5,
    ) -> list[QueryResult]:
        """Performs semantic code search filtered by repository ID and branch name.

        Args:
            repository_id (int): Target repository ID.
            branch_name (str): Target branch name (e.g. 'main', 'dev').
            query (str): Natural language search prompt.
            top_k (int, optional): Maximum number of hits to return (defaults to 5).

        Returns:
            list[QueryResult]: Ranked list of search result hits.
        """
        stmt = select(Branch).where(
            Branch.repository_id == repository_id,
            Branch.branch_name == branch_name,
        )
        res = await self.db_session.execute(stmt)
        branch = res.scalar_one_or_none()

        if branch is None:
            logger.warning(
                "Branch '%s' for repository_id=%d not found.",
                branch_name,
                repository_id,
            )
            return []

        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            branch_id=branch.id,
        )
