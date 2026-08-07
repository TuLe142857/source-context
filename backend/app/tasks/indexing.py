import asyncio
import logging
from pathlib import Path
from typing import Any
from celery import shared_task

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.postgres import database
from app.embedding.embedding_pipeline import process_uast_batch_llm_summaries
from app.embedding.utils import extract_summarizable_nodes
from app.enums import BranchIndexingStatus, IndexingJobStatus
from app.graph import build_call_graph_for_project, save_file_node
from app.graph.model import ProjectNodeModel
from app.model.branch import Branch
from app.model.indexing_job import IndexingJob
from app.model.project import Project
from app.model.repository import Repository
from app.parser import UnsupportedLanguageError
from app.parser.languages import get_language_registry
from app.parser.uast import UASTNode
from app.repository_manager.git_client import GitClient
from app.scip import scip_pb2
from app.scip.sandbox import get_scip_sandbox_registry

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
        f"{settings.repository_workspace_root}/repo_{repo.id}/{branch.branch_name}"
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
        "Start parsing source code of project: project_id= %d, project_root: %s, total files = %d",
        project_id,
        str(project_root),
        len(files),
    )

    # create ProjectNode in neo4j
    project_node_model: ProjectNodeModel | None = ProjectNodeModel.nodes.get_or_none(
        uid=project_id
    )
    
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

            logger.info(
                "Start parsing file. Filename= %s, path= %s",
                file.name,
                str(file.relative_to(project_root)),
            )
            ts_tree = parser.parse(file_content_bytes)
            uast_root_node = converter.convert(
                ts_tree, file_content_bytes, str(file.relative_to(project_root))
            )
            results.append(uast_root_node)

            logger.info("Parsing file %s completed", file.name)

            logger.info("Start saving nodes in file file %s to neo4j", file.name)
            save_file_node(uast_root_node, project_id, file_content_bytes, file.suffix)
            logger.info("Saving nodes in file %s to neo4j success", file.name)

        except UnsupportedLanguageError:
            logger.info(
                "Ignore file %s, because can't find language config for this file",
                file.name,
            )

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
    project_root_relative = project_root.relative_to(settings.repository_workspace_root)

    logger.info(
        "Stage 3 (Combined): SCIP indexing and Code Graph DB construction for project_id=%d (%s) at %s",
        project_id,
        language,
        project_root,
    )
    sandbox_registry = get_scip_sandbox_registry()
    sandbox = sandbox_registry.get_sandbox(language)
    if sandbox is None:
        raise ValueError(f"No SCIP sandbox available for language: {language}")

    logger.info("Start indexing scip")
    index_bytes = sandbox.index(str(project_root_relative))
    index = scip_pb2.Index()
    index.ParseFromString(index_bytes)
    logger.info(f"SCIP indexing successful, total documents = {len(index.documents)}")

    logger.info("Start building call graph")
    build_call_graph_for_project(project_id, index, project_root)
    logger.info("Build call graph successful")

    return {"status": "scip_graph_built", "language": language, "neo4j_nodes": 0}


async def build_vector_embeddings_stage(
    project_id: int,
    file_roots: list[UASTNode],
    local_path: Path,
    root_dir: str,
    branch_id: int,
    workspace_id: int,
) -> dict[str, Any]:
    """Stage 4: Generates vector embeddings for UAST nodes and upserts to Qdrant Vector DB.

    Args:
        project_id (int): Target project ID.
        file_roots (list[UASTNode]): List of parsed root UAST nodes for each file in project.
        local_path (Path): Path to branch source code directory.
        root_dir (str): Sub-directory root path inside branch.
        branch_id (int): Target branch ID.
        workspace_id (int): Target workspace ID.

    Returns:
        dict[str, Any]: Embedding stage completion status and point count.
    """
    project_root = local_path / root_dir
    logger.info(
        "Stage 4: Building Vector DB Embeddings for project_id=%d (%d files) at %s",
        project_id,
        len(file_roots),
        project_root,
    )

    candidate_tuples: list[tuple[UASTNode, UASTNode, Path]] = []
    for root_node in file_roots:
        file_path_str = getattr(root_node, "file_path", None) or ""
        file_path = project_root / file_path_str if file_path_str else project_root

        summarizable_nodes = extract_summarizable_nodes(root_node)
        for target_node in summarizable_nodes:
            candidate_tuples.append((root_node, target_node, file_path))

    if not candidate_tuples:
        logger.info("No summarizable nodes found for project_id=%d", project_id)
        return {"status": "vector_embedded", "qdrant_points": 0}

    embedded_batches = await asyncio.to_thread(
        process_uast_batch_llm_summaries,
        workspace_id=workspace_id,
        branch_id=branch_id,
        candidate_tuples=candidate_tuples,
        batch_size=50,
    )

    total_points = sum(len(b) for b in embedded_batches)
    logger.info(
        "Stage 4 complete: Embedded and upserted %d vector points to Qdrant for project_id=%d",
        total_points,
        project_id,
    )
    return {"status": "vector_embedded", "qdrant_points": total_points}


async def execute_branch_indexing_pipeline(
    workspace_id: int,
    branch_id: int,
    job_id: int,
    db: AsyncSession,
) -> None:
    """Executes the complete indexing pipeline for one Branch.

    Args:
        workspace_id (int): Target workspace ID.
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
        job.status = IndexingJobStatus.PROCESSING
        job.progress_pct = 20
        await db.commit()

        branch_res = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = branch_res.scalar_one_or_none()

        # Update branch status to indexing
        if branch is not None:
            branch.indexing_status = BranchIndexingStatus.INDEXING
            await db.commit()
         
        destination, _ = await download_branch_source_stage(branch_id=branch_id, db=db)

        # Fetch projects under this branch for this workspace
        proj_res = await db.execute(
            select(Project).where(
                Project.branch_id == branch_id,
                (Project.workspace_id == workspace_id)
                | (Project.workspace_id.is_(None)),
            )
        )
        projects = proj_res.scalars().all()

        # Step 2: Tree-sitter AST Parsing
        job.status = IndexingJobStatus.PROCESSING
        job.progress_pct = 40

        await db.commit()
        uast_parse_results: dict[int, list[UASTNode]] = {}
        for p in projects:
            parse_result = await parse_tree_sitter_ast_stage(
                project_id=p.id, root_dir=p.root_dir, local_path=destination
            )
            uast_parse_results[p.id] = parse_result

        # Step 3: SCIP Indexing & Code Graph Building (Single Combined Stage)
        job.status = IndexingJobStatus.PROCESSING
        job.progress_pct = 70
        await db.commit()
        for p in projects:
            await run_scip_and_build_graph_stage(
                p.id, p.root_dir, str(p.language), destination
            )

        # Step 4: Vector DB Embeddings Construction
        job.status = IndexingJobStatus.PROCESSING
        job.progress_pct = 90
        await db.commit()
        for p in projects:
            file_roots = uast_parse_results.get(p.id, [])
            await build_vector_embeddings_stage(
                project_id=p.id,
                file_roots=file_roots,
                local_path=destination,
                root_dir=p.root_dir,
                branch_id=branch_id,
                workspace_id=workspace_id,
            )

        job.status = IndexingJobStatus.COMPLETED
        job.progress_pct = 100
        job.error_message = None

        if branch is not None:
            branch.indexing_status = BranchIndexingStatus.INDEXED

        await db.commit()
        logger.info(
            "IndexingJob %d for branch_id=%d (workspace_id=%d) COMPLETED successfully.",
            job_id,
            branch_id,
            workspace_id,
        )

    except Exception as exc:
        logger.exception("IndexingJob %d failed: %s", job_id, exc)
        job.status = IndexingJobStatus.FAILED
        job.error_message = str(exc)

        branch_err_res = await db.execute(select(Branch).where(Branch.id == branch_id))
        err_branch = branch_err_res.scalar_one_or_none()
        if err_branch is not None:
            err_branch.indexing_status = BranchIndexingStatus.FAILED

        await db.commit()


@shared_task(name="index_branch_task")
def index_branch_task(workspace_id: int, branch_id: int, job_id: int) -> None:
    """Celery background task wrapper for executing branch indexing pipeline.

    Args:
        workspace_id (int): Target workspace ID.
        branch_id (int): Target branch ID.
        job_id (int): IndexingJob ID.
    """
    logger.info(
        "Celery worker received index_branch_task(workspace_id=%d, branch_id=%d, job_id=%d)",
        workspace_id,
        branch_id,
        job_id,
    )

    async def _runner() -> None:
        try:
            await database.engine.dispose()
            async with database.async_session_factory() as session:
                await execute_branch_indexing_pipeline(
                    workspace_id, branch_id, job_id, session
                )
        finally:
            await database.engine.dispose()

    asyncio.run(_runner())
