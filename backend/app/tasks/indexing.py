import asyncio
import logging
from pathlib import Path
from typing import Any
from celery import shared_task

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.postgres import database
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.project import Project
from app.model.repository import Repository
from app.repository_manager.git_client import GitClient
from app.parser.uast import UASTNode
from app.parser.languages import get_language_registry
from app.parser import UnsupportedLanguageError
from app.scip.sandbox import get_scip_sandbox_registry
from app.scip import scip_pb2
from app.graph import save_file_node, build_call_graph_for_project
from app.graph.model import ProjectNodeModel

logger = logging.getLogger(__name__)


async def download_branch_source_stage(
    branch_id: int,
    db: AsyncSession,
) -> tuple[Path, str]:
    """Stage 1: Clones/updates the source code for a specific branch using GitClient.

    Args:
        branch_id (int): Target branch ID.
        db (AsyncSession): Database session.

    Returns:
        tuple[Path, str]: Local storage Path and actual commit SHA.
    """
    stmt = (
        select(Branch, Repository)
        .join(Repository, Branch.repository_id == Repository.id)
        .where(Branch.id == branch_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if row is None:
        raise ValueError(f"Branch with ID {branch_id} not found.")

    branch: Branch = row[0]
    repo: Repository = row[1]

    destination = Path(
        branch.local_path
        or f"{settings.repository_workspace_root}/ws_{repo.project_id}/{repo.name}/{branch.branch_name}"
    )

    git_client = GitClient(timeout_seconds=settings.git_command_timeout_seconds)
    metadata = git_client.clone_or_update_branch(
        repository_url=repo.git_url,
        branch_name=branch.branch_name,
        destination=destination,
    )

    branch.local_path = str(destination)
    branch.commit_hashed = metadata.commit_sha
    await db.commit()

    logger.info(
        "Stage 1 complete: Branch %s cloned to %s (commit: %s)",
        branch.branch_name,
        destination,
        metadata.commit_sha,
    )
    return destination, metadata.commit_sha


async def parse_tree_sitter_ast_stage(
    project_id: int,
    root_dir: str,
    local_path: Path,
) -> list[UASTNode]:
    """
    Stage 2: Template handler for Tree-sitter AST parsing:
        - Parser files to uast-nodes
        - Saves to neo4j
    Args:
        project_id (int): Target project ID.
        root_dir (str): Sub-directory root path inside branch.
        local_path (Path): Path to branch source code directory.

    Returns:
        list[root_node], every root node is the root node of a files. root_node.path is relative from project.

    """

    project_root = local_path / root_dir

    if not (project_root.exists()) or not (project_root.is_dir()):
        raise ValueError(f"Invalid root path {str(project_root)}")

    logger.info(
        "Stage 2 (Template): Tree-sitter AST parsing for branch_id=%d at %s. Project root dir: %s",
        project_id,
        str(project_root),
        local_path,
    )

    files = [f for f in project_root.rglob("*") if f.is_file()]
    logger.info(
        "Start parsing source code of project: project_id= %d, project_root: %s, total files = %d", project_id, str(project_root), len(files)
    )

    # create ProjectNode in neo4j
    project_node_model: ProjectNodeModel|None = ProjectNodeModel.nodes.get_or_none(uid=project_id) # type: ignore
    if project_node_model is None:
        new_project_node_model = ProjectNodeModel(uid=project_id)
        new_project_node_model.save()

    results: list[UASTNode] = []
    lang_registry = get_language_registry()
    for file in files:
        try:
            parser = lang_registry.get_parser_for_file(file.name)
            converter = lang_registry.get_converter_for_file(file.name)

            file_content_bytes = file.read_bytes()


            logger.info("Start parsing file. Filename= %s, path= %s", file.name, str(file.relative_to(project_root)))
            ts_tree = parser.parse(file_content_bytes)
            uast_root_node = converter.convert(ts_tree, file_content_bytes, str(file.relative_to(project_root)))
            results.append(uast_root_node)

            logger.info("Parsing file %s completed", file.name)

            logger.info("Start saving nodes in file file %s to neo4j", file.name)
            save_file_node(uast_root_node, project_id)
            logger.info("Saving nodes in file %s to neo4j success", file.name)

        except UnsupportedLanguageError:
            logger.info("Ignore file %s, because can't find language config for this file", file.name)

    return results


async def run_scip_and_build_graph_stage(
    project_id: int,
    root_dir: str,
    language: str,
    local_path: Path,
) -> dict[str, Any]:
    """
    Stage 3: Combined template handler for running SCIP indexer & building Code Graph DB (Neo4j).

    - Index SCIP
    - Build call graph
    Args:
        project_id (int): Target project ID.
        root_dir (str): Sub-directory root path inside branch.
        language (str): Programming language target.
        local_path (Path): Path to branch source code directory.

    Returns:
        dict[str, Any]: SCIP indexing and Code Graph construction result placeholder.
    """
    project_root = local_path / root_dir

    logger.info(
        "Stage 3 (Combined): SCIP indexing and Code Graph DB construction for project_id=%d (%s) at %s",
        project_id,
        language,
        project_root,
    )
    sandbox_registry = get_scip_sandbox_registry()
    sandbox = sandbox_registry.get_sandbox(language)

    logger.info("Start indexing scip")
    index_bytes = sandbox.index(root_dir)
    index = scip_pb2.Index()
    index.ParseFromString(index_bytes)
    logger.info("SCIP indexing successful")

    logger.info("Start building call graph")
    build_call_graph_for_project(project_id, index)
    logger.info("Build call graph successful")

    return {"status": "scip_graph_built", "language": language, "neo4j_nodes": 0}


async def build_vector_embeddings_stage(project_id: int) -> dict[str, Any]:
    """Stage 4: Template handler for vector embedding generation & Qdrant storage.

    Args:
        project_id (int): Target project ID.

    Returns:
        dict[str, Any]: Embedding task result placeholder.
    """
    logger.info(
        "Stage 4 (Template): Building Vector DB Embeddings for project_id=%d",
        project_id,
    )
    return {"status": "vector_embedded", "qdrant_points": 0}


async def execute_branch_indexing_pipeline(
    branch_id: int,
    job_id: int,
    db: AsyncSession,
) -> None:
    """Executes the complete indexing pipeline for one Branch.

    Args:
        branch_id (int): Target branch ID.
        job_id (int): IndexingJob ID.
        db (AsyncSession): Database session.
    """
    job_res = await db.execute(select(IndexingJob).where(IndexingJob.id == job_id))
    job = job_res.scalar_one_or_none()
    if job is None:
        logger.error("IndexingJob %d not found.", job_id)
        return

    try:
        # Step 1: Download/Clone Branch Source
        job.status = "DOWNLOADING_SOURCE"
        job.progress_pct = 20
        await db.commit()

        destination, _ = await download_branch_source_stage(branch_id, db)

        # Fetch projects under this branch
        proj_res = await db.execute(
            select(Project).where(Project.branch_id == branch_id)
        )
        projects = proj_res.scalars().all()

        # Step 2: Tree-sitter AST Parsing
        job.status = "PARSING_AST"
        job.progress_pct = 40

        await db.commit()
        uast_parse_results: dict[int, list[UASTNode]] = {}
        for p in projects:
            parse_result = await parse_tree_sitter_ast_stage(
                project_id=p.id, root_dir=p.root_dir, local_path=destination
            )
            uast_parse_results[p.id] = parse_result

        # Step 3: SCIP Indexing & Code Graph Building (Single Combined Stage)
        job.status = "SCIP_AND_GRAPH"
        job.progress_pct = 70
        await db.commit()
        for p in projects:
            await run_scip_and_build_graph_stage(
                p.id, p.root_dir, str(p.language), destination
            )

        # Step 4: Vector DB Embeddings Construction
        job.status = "BUILDING_EMBEDDINGS"
        job.progress_pct = 90
        await db.commit()
        for p in projects:
            await build_vector_embeddings_stage(p.id)

        job.status = "COMPLETED"
        job.progress_pct = 100
        job.error_message = None
        await db.commit()
        logger.info(
            "IndexingJob %d for branch_id=%d COMPLETED successfully.",
            job_id,
            branch_id,
        )

    except Exception as exc:
        logger.exception("IndexingJob %d failed: %s", job_id, exc)
        job.status = "FAILED"
        job.error_message = str(exc)
        await db.commit()


@shared_task(name="index_branch_task")
def index_branch_task(branch_id: int, job_id: int) -> None:
    """Celery background task wrapper for executing branch indexing pipeline.

    Args:
        branch_id (int): Target branch ID.
        job_id (int): IndexingJob ID.
    """
    logger.info(
        "Celery worker received index_branch_task(branch_id=%d, job_id=%d)",
        branch_id,
        job_id,
    )

    async def _runner() -> None:
        async with database.async_session_factory() as session:
            await execute_branch_indexing_pipeline(branch_id, job_id, session)

    asyncio.run(_runner())
