"""Main embedding pipeline module orchestrating UAST parsing, node enhancement, structured formatting, batch LLM summarization, Voyage AI embedding, and Qdrant batch upsert."""

import io
import logging
from pathlib import Path
import sys
from typing import Any

from app.core.config import settings
from app.core.qdrant import QdrantVectorStore
from app.embedding.inference import get_openai_client, get_summary
from app.embedding.utils import (
    EnrichedNodeData,
    chunk_list,
    extract_clean_identifiers,
    extract_node_signature,
    extract_source_code,
    extract_summarizable_nodes,
    format_node_for_embedding,
)
from app.embedding.voyage_embedder import get_voyage_embedder
from app.parser.languages import get_language_registry
from app.parser.uast import UASTNode

# Setup logger for pipeline execution
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Ensure UTF-8 output encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
elif getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def parse_and_convert_file(file_path: Path) -> UASTNode | None:
    """Sets up language parser and converter for a file, converts source, and returns UAST root.

    Args:
        file_path (Path): Path to source file.

    Returns:
        UASTNode | None: Parsed UAST root node or None if unsupported/error.
    """
    if not file_path.exists() or not file_path.is_file():
        logger.warning("File not found: %s", file_path)
        return None

    language_registry = get_language_registry()

    try:
        parser = language_registry.get_parser_for_file(file_path.name)
        converter = language_registry.get_converter_for_file(file_path.name)
    except Exception as exc:
        logger.error("Could not setup parser/converter for %s: %s", file_path.name, exc)
        return None

    source_bytes = file_path.read_bytes()
    ts_tree = parser.parse(source_bytes)

    uast_root = converter.convert(
        ts_tree,
        source_bytes=source_bytes,
        file_path=str(file_path),
    )

    return uast_root


def batch_embed_nodes_template(
    enhanced_batch: list[EnrichedNodeData],
    vector_store: QdrantVectorStore | None = None,
) -> list[EnrichedNodeData]:
    print(enhanced_batch[0].branch_id)
    """Embeds enriched node chunks with Voyage AI (voyage-code-3) and upserts vector points to Qdrant Vector DB.

    Args:
        enhanced_batch (list[EnrichedNodeData]): Batch of enriched nodes with structured text and LLM summaries.
        vector_store (QdrantVectorStore | None): Optional target QdrantVectorStore instance.

    Returns:
        list[EnrichedNodeData]: Enriched nodes with vector embeddings populated.
    """
    if not enhanced_batch:
        return []

    embedder = get_voyage_embedder()
    store = vector_store or QdrantVectorStore()

    texts = [
        item.formatted_embed_text or item.summary or item.signature
        for item in enhanced_batch
    ]

    embeddings = embedder.embed_documents(texts)
    for idx, item in enumerate(enhanced_batch):
        if idx < len(embeddings):
            item.embedding = embeddings[idx]

    # Batch upsert to Qdrant Vector DB
    store.upsert_batch(enhanced_batch, vector_size=1024)
    return enhanced_batch


def process_uast_batch_llm_summaries(
    workspace_id: int,
    branch_id: int,
    candidate_tuples: list[tuple[UASTNode, UASTNode, Path]],
    batch_size: int = 50,
    max_nodes: int | None = None,
    client: Any | None = None,
    model: str | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> list[list[EnrichedNodeData]]:
    """Enhances node metadata, generates LLM summaries, computes Voyage AI embeddings, and upserts points to Qdrant in batches.

    Args:
        workspace_id (int): Target workspace ID.
        branch_id (int): Target branch ID.
        candidate_tuples (list[tuple[UASTNode, UASTNode, Path]]): Tuples of (root_node, target_node, file_path).
        batch_size (int, optional): Number of nodes per batch (default 50).
        max_nodes (int | None, optional): Optional max node limit (e.g. 5 or 10 to save tokens).
        client (Any | None, optional): Optional preloaded OpenAI client instance.
        model (str | None, optional): Custom OpenAI model name (defaults to gpt-4o-mini).
        vector_store (QdrantVectorStore | None, optional): Shared QdrantVectorStore instance.

    Returns:
        list[list[EnrichedNodeData]]: List of embedded node batches.
    """
    if not candidate_tuples:
        return []

    if max_nodes is not None and max_nodes > 0:
        candidate_tuples = candidate_tuples[:max_nodes]
        logger.info(
            "Token savings mode: Limited execution to first %d nodes.",
            len(candidate_tuples),
        )

    openai_client = client if client is not None else get_openai_client()
    target_model = model or settings.OPENAI_MODEL or "gpt-4o-mini"
    qdrant_store = vector_store or QdrantVectorStore()
    all_embedded_batches: list[list[EnrichedNodeData]] = []

    total_nodes = len(candidate_tuples)
    logger.info(
        "Starting Batch Pipeline | Model: %s | Total Nodes: %d | Batch Size: %d",
        target_model,
        total_nodes,
        batch_size,
    )

    batch_idx = 1
    for chunk in chunk_list(candidate_tuples, batch_size):
        logger.info(
            "--- Batch %d/%d: Summarizing & Embedding %d nodes ---",
            batch_idx,
            (total_nodes + batch_size - 1) // batch_size,
            len(chunk),
        )
        enhanced_batch: list[EnrichedNodeData] = []
        node_num = 1

        for root_node, target_node, file_path in chunk:
            signature = extract_node_signature(target_node)
            source_code = extract_source_code(root_node, target_node, file_path)

            logger.info(
                "Summarizing node [%d/%d] in batch %d: %s (%s)",
                node_num,
                len(chunk),
                batch_idx,
                target_node.name or "unnamed",
                getattr(target_node, "kind", target_node.node_type),
            )

            # 1. Get OpenAI LLM summary for node
            summary = get_summary(
                root_node=root_node,
                target_node=target_node,
                file_path=file_path,
                signature=signature,
                client=openai_client,
                model=target_model,
            )

            identifiers = extract_clean_identifiers(target_node)

            # 2. Format structured text representation for embedding
            formatted_embed_text = format_node_for_embedding(
                node=target_node,
                summary=summary,
                identifiers=identifiers,
            )

            # 3. Build enriched node data
            item = EnrichedNodeData(
                workspace_id=workspace_id,
                branch_id=branch_id,
                node_id=target_node.id,
                node_type=target_node.node_type,
                kind=getattr(target_node, "kind", target_node.node_type),
                name=target_node.name or "unnamed",
                file_path=str(file_path),
                signature=signature,
                source_code=source_code,
                docstring=target_node.docstring,
                summary=summary,
                identifiers=identifiers,
                formatted_embed_text=formatted_embed_text,
            )
            enhanced_batch.append(item)
            node_num += 1

        # 4. Embed & batch upsert directly to Qdrant Vector DB
        embedded_batch = batch_embed_nodes_template(
            enhanced_batch=enhanced_batch,
            vector_store=qdrant_store,
        )
        all_embedded_batches.append(embedded_batch)

        logger.info("Batch %d completed & uploaded to Qdrant.", batch_idx)
        batch_idx += 1

    return all_embedded_batches


def run_embedding_pipeline(
    source_paths: list[Path],
    workspace_id: int = 1,
    branch_id: int = 1,
    batch_size: int = 50,
    max_nodes: int | None = None,
    client: Any | None = None,
    model: str | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> list[list[EnrichedNodeData]]:
    """Runs full pipeline across multiple files: Parse -> Extract -> Batch LLM Summaries -> Voyage Embed -> Qdrant Batch Upsert.

    Args:
        source_paths (list[Path]): List of source code file paths to process.
        workspace_id (int, optional): Target workspace ID (defaults to 1).
        branch_id (int, optional): Target branch ID (defaults to 1).
        batch_size (int, optional): Batch size threshold (default 50).
        max_nodes (int | None, optional): Max nodes limit to process (e.g. 5 or 10 to save tokens).
        client (Any | None, optional): Optional preloaded OpenAI client instance.
        model (str | None, optional): Custom OpenAI model name.
        vector_store (QdrantVectorStore | None, optional): Shared QdrantVectorStore instance.

    Returns:
        list[list[EnrichedNodeData]]: Processed & embedded node batches.
    """
    candidate_tuples: list[tuple[UASTNode, UASTNode, Path]] = []

    for file_path in source_paths:
        root_node = parse_and_convert_file(file_path)
        if root_node is None:
            continue

        summarizable_nodes = extract_summarizable_nodes(root_node)
        for target_node in summarizable_nodes:
            candidate_tuples.append((root_node, target_node, file_path))

    return process_uast_batch_llm_summaries(
        workspace_id=workspace_id,
        branch_id=branch_id,
        candidate_tuples=candidate_tuples,
        batch_size=batch_size,
        max_nodes=max_nodes,
        client=client,
        model=model,
        vector_store=vector_store,
    )


if __name__ == "__main__":
    sample_paths = [
        Path(
            r"C:\Hieu\TTTN\source-context\backend\data\sample_data\app\api\routes\items.py"
        ),
        Path(r"C:\Hieu\TTTN\source-context\backend\data\sample_data\app\models.py"),
    ]

    logger.info("Running Embedding Pipeline demonstration on sample paths...")
    # Demo running with max_nodes=5 to save OpenAI tokens
    batches = run_embedding_pipeline(
        source_paths=[p for p in sample_paths if p.exists()],
        batch_size=5,
        max_nodes=5,
    )
    logger.info("Pipeline finished. Produced %d batches.", len(batches))
