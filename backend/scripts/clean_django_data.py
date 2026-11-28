"""Script to cleanly purge all Django-related data from PostgreSQL, Neo4j, and Qdrant.

Ensures no duplicate nodes, embeddings, or metadata remain prior to re-indexing.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure backend directory is in sys.path so 'app' can be imported
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.postgres import database
from app.core.qdrant import get_qdrant_client
from app.enums import BranchIndexingStatus
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.project import Project
from app.model.repository import Repository
from app.model.workspace_branch import WorkspaceBranch
from app.model.workspace_repository import WorkspaceRepository

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def find_django_entities(
    session: Any,
) -> tuple[list[Repository], list[int], list[int], list[int]]:
    """Finds all Django repositories, branches, projects, and jobs.

    Args:
        session: SQLAlchemy AsyncSession.

    Returns:
        tuple containing (repositories, branch_ids, project_ids, job_ids).
    """
    stmt = (
        select(Repository)
        .where(
            (Repository.name.ilike("%django%")) | (Repository.git_url.ilike("%django%"))
        )
        .options(
            selectinload(Repository.branches).selectinload(Branch.projects),
            selectinload(Repository.branches).selectinload(Branch.indexing_jobs),
        )
    )
    res = await session.scalars(stmt)
    repos = list(res.all())

    branch_ids: list[int] = []
    project_ids: list[int] = []
    job_ids: list[int] = []

    for r in repos:
        for b in r.branches:
            branch_ids.append(b.id)
            for p in b.projects:
                project_ids.append(p.id)
            for j in b.indexing_jobs:
                job_ids.append(j.id)

    # Also search for standalone projects or branches containing 'django'
    proj_stmt = select(Project.id).where(Project.root_dir.ilike("%django%"))
    extra_proj_res = await session.scalars(proj_stmt)
    for p_id in extra_proj_res.all():
        if p_id not in project_ids:
            project_ids.append(p_id)

    return repos, branch_ids, project_ids, job_ids


def clean_neo4j(project_ids: list[int]) -> int:
    """Removes all Neo4j graph nodes and relationships associated with Django projects.

    Args:
        project_ids: List of Django project IDs.

    Returns:
        int: Number of deleted nodes.
    """
    try:
        from neomodel import db

        total_deleted = 0

        if project_ids:
            query = """
            MATCH (p:Project)
            WHERE p.uid IN $project_ids
            OPTIONAL MATCH (p)-[:INCLUDES]->(f:File)
            OPTIONAL MATCH (n:Node {file_node_uid: f.uid})
            OPTIONAL MATCH (p)-[:EXPOSES_API]->(ep)
            OPTIONAL MATCH (p)-[:HAS_API_CALL]->(ac)
            DETACH DELETE n, f, ep, ac, p
            """
            result, _ = db.cypher_query(query, {"project_ids": project_ids})
            logger.info("Executed Neo4j deletion for project IDs: %s", project_ids)

        # Catch any orphaned File or Node nodes with path containing django
        cleanup_query = """
        MATCH (f:File)
        WHERE f.relative_path CONTAINS 'django' OR f.name CONTAINS 'django'
        OPTIONAL MATCH (n:Node {file_node_uid: f.uid})
        DETACH DELETE n, f
        """
        db.cypher_query(cleanup_query)

        # Catch any Project node named django
        proj_cleanup_query = """
        MATCH (p:Project)
        WHERE toLower(p.name) CONTAINS 'django'
        DETACH DELETE p
        """
        db.cypher_query(proj_cleanup_query)

        logger.info("Neo4j graph cleanup for Django completed successfully.")
        return total_deleted
    except Exception as exc:
        logger.warning("Could not clean Neo4j (is Neo4j running?): %s", exc)
        return 0


def clean_qdrant(branch_ids: list[int]) -> int:
    """Purges all Django vector embeddings from Qdrant.

    Args:
        branch_ids: List of Django branch IDs.

    Returns:
        int: Total deleted points or status code.
    """
    try:
        from qdrant_client.http import models as qmodels

        client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION_NAME or "code_chunks"

        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            logger.info("Qdrant collection '%s' does not exist.", collection_name)
            return 0

        # Delete by branch_id
        for b_id in branch_ids:
            logger.info("Deleting Qdrant points for branch_id=%d...", b_id)
            client.delete(
                collection_name=collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="branch_id",
                                match=qmodels.MatchValue(value=b_id),
                            )
                        ]
                    )
                ),
            )

        # Delete any points whose file_path contains django
        logger.info("Deleting Qdrant points with file_path containing 'django'...")
        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="file_path",
                            match=qmodels.MatchText(text="django"),
                        )
                    ]
                )
            ),
        )

        logger.info("Qdrant vector cleanup for Django completed successfully.")
        return len(branch_ids)
    except Exception as exc:
        logger.warning("Could not clean Qdrant (is Qdrant running?): %s", exc)
        return 0


async def clean_postgres(
    session: Any,
    repos: list[Repository],
    branch_ids: list[int],
    project_ids: list[int],
    job_ids: list[int],
    reset_only: bool = False,
) -> None:
    """Cleans or resets Django records in PostgreSQL.

    Args:
        session: SQLAlchemy AsyncSession.
        repos: List of Django Repository models.
        branch_ids: List of Django branch IDs.
        project_ids: List of Django project IDs.
        job_ids: List of Django indexing job IDs.
        reset_only: If True, resets branch status and deletes jobs/projects instead of deleting repository.
    """
    if reset_only:
        logger.info("Resetting branch indexing status to UNINDEXED...")
        for b_id in branch_ids:
            branch = await session.get(Branch, b_id)
            if branch:
                branch.indexing_status = BranchIndexingStatus.UNINDEXED

        if job_ids:
            logger.info("Deleting indexing jobs: %s", job_ids)
            await session.execute(
                delete(IndexingJob).where(IndexingJob.id.in_(job_ids))
            )

        if project_ids:
            logger.info("Deleting projects: %s", project_ids)
            await session.execute(delete(Project).where(Project.id.in_(project_ids)))

        await session.commit()
        logger.info("PostgreSQL Django metadata reset to UNINDEXED.")
    else:
        logger.info("Purging Django repositories completely from PostgreSQL...")
        for repo in repos:
            repo_id = repo.id
            repo_name = repo.name
            logger.info("Deleting Repository id=%d ('%s')...", repo_id, repo_name)
            # Remove explicit workspace links
            await session.execute(
                delete(WorkspaceRepository).where(
                    WorkspaceRepository.repository_id == repo_id
                )
            )
            for b in repo.branches:
                await session.execute(
                    delete(WorkspaceBranch).where(WorkspaceBranch.branch_id == b.id)
                )
            await session.delete(repo)

        await session.commit()
        logger.info("PostgreSQL Django repositories deleted successfully.")


async def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Clean Django metadata from PostgreSQL, Neo4j, and Qdrant."
    )
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Reset branch status to UNINDEXED and clear jobs instead of deleting the repository.",
    )
    args = parser.parse_args()

    logger.info("=== Starting Django Data Cleanup ===")
    async with database.async_session_factory() as session:
        repos, branch_ids, project_ids, job_ids = await find_django_entities(session)

        logger.info(
            "Found %d Django repositories: %s", len(repos), [r.name for r in repos]
        )
        logger.info("Associated Branch IDs: %s", branch_ids)
        logger.info("Associated Project IDs: %s", project_ids)
        logger.info("Associated IndexingJob IDs: %s", job_ids)

        # 1. Clean Neo4j
        logger.info("--- Step 1: Cleaning Neo4j ---")
        clean_neo4j(project_ids)

        # 2. Clean Qdrant
        logger.info("--- Step 2: Cleaning Qdrant ---")
        clean_qdrant(branch_ids)

        # 3. Clean PostgreSQL
        logger.info("--- Step 3: Cleaning PostgreSQL ---")
        await clean_postgres(
            session, repos, branch_ids, project_ids, job_ids, reset_only=args.reset_only
        )

    logger.info("=== Django Data Cleanup Finished Successfully! ===")


if __name__ == "__main__":
    asyncio.run(main())
