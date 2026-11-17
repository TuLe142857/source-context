"""Zero-LLM indexing module for fast, deterministic code embedding without calling an LLM.

Extracts AST metadata, docstrings, and signatures to build rich structured text representations
for Voyage AI code embeddings and populates clean summaries for Neo4j and search payloads.
"""

import logging
from pathlib import Path
import re

from app.core.qdrant import QdrantVectorStore
from app.embedding.utils import (
    EnrichedNodeData,
    chunk_list,
    extract_clean_identifiers,
    extract_node_signature,
    extract_source_code,
)
from app.embedding.voyage_embedder import batch_embed_nodes_template
from app.engine.parser.uast.node import TypeDefinitionNode, UASTNode

logger = logging.getLogger(__name__)


def split_identifier(name: str) -> str:
    """Splits snake_case and camelCase identifiers into space-separated natural language words.

    Args:
        name (str): Identifier name (e.g. 'get_current_active_superuser' or 'TokenPayload').

    Returns:
        str: Lowercase space-separated words (e.g. 'get current active superuser' or 'token payload').
    """
    if not name:
        return ""
    # Split camelCase and PascalCase
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    # Split snake_case and hyphens
    s = s.replace("_", " ").replace("-", " ")
    return " ".join(s.lower().split())


def find_enclosing_scope_name(root_node: UASTNode, target_node: UASTNode) -> str | None:
    """Finds the name of the enclosing class or type definition for a target node.

    Args:
        root_node (UASTNode): The root UAST node of the file.
        target_node (UASTNode): The target node to locate.

    Returns:
        str | None: Name of enclosing class if found, otherwise None.
    """
    target_id = target_node.id
    scope_name: str | None = None

    def _traverse(node: UASTNode, current_class: str | None) -> bool:
        nonlocal scope_name
        if node.id == target_id:
            scope_name = current_class
            return True

        new_class = current_class
        if isinstance(node, TypeDefinitionNode) and node.name:
            new_class = node.name

        for child in node.children:
            if _traverse(child, new_class):
                return True
        return False

    _traverse(root_node, None)
    return scope_name


def extract_ast_summary(
    target_node: UASTNode,
    signature: str,
    docstring: str | None,
    file_path: str | Path,
    scope_name: str | None = None,
) -> str:
    """Extracts a clean, human-readable summary for Neo4j and search payloads without calling an LLM.

    Prefers the first sentence of the docstring (PEP 257 / standard docstring convention).
    Falls back to a structured description based on node type, signature, and location.

    Args:
        target_node (UASTNode): The target node.
        signature (str): The node signature.
        docstring (str | None): The node docstring if present.
        file_path (str | Path): Path to the source file.
        scope_name (str | None, optional): Name of enclosing class if applicable. Defaults to None.

    Returns:
        str: A clean 1-2 sentence summary string.
    """
    if docstring and docstring.strip():
        clean_doc = docstring.strip().strip('"""').strip("'''").strip()
        lines = [line.strip() for line in clean_doc.splitlines() if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) > 10:
                return first_line

    path_obj = Path(file_path)
    clean_path = path_obj.name
    node_name = target_node.name or "unnamed"

    if isinstance(target_node, TypeDefinitionNode):
        return f"Class `{node_name}` defined in `{clean_path}`."

    if scope_name:
        return f"Method `{node_name}` of class `{scope_name}` ({signature}) defined in `{clean_path}`."

    return f"Function `{node_name}` ({signature}) defined in `{clean_path}`."


def build_embed_text(
    file_path: str,
    scope_name: str | None,
    node_type: str,
    symbol_name: str,
    signature: str,
    docstring: str | None,
    code_snippet: str,
) -> str:
    """Builds an enriched, structured text representation for code vector embedding with Voyage AI.

    Omits empty or None fields to prevent vector noise.

    Args:
        file_path (str): Relative or file path.
        scope_name (str | None): Enclosing class or scope name.
        node_type (str): Type of node ('function', 'type_definition', etc.).
        symbol_name (str): Name of the symbol.
        signature (str): Formal signature of the construct.
        docstring (str | None): Raw docstring content if present.
        code_snippet (str): Source code implementation snippet.

    Returns:
        str: Multiline structured text chunk optimized for Voyage AI code embedding.
    """
    clean_keywords = split_identifier(symbol_name)
    clean_doc = docstring.strip().strip('"""').strip("'''").strip() if docstring else ""

    parts = [
        f"File: {file_path}",
        f"Scope: {scope_name}" if scope_name else None,
        f"Symbol: {node_type} {signature}",
        f"Keywords: {clean_keywords}" if clean_keywords else None,
        f"Docstring: {clean_doc}" if clean_doc else None,
        f"Code:\n{code_snippet[:1500]}" if code_snippet else None,
    ]
    return "\n".join(p for p in parts if p)


def process_uast_batch_no_llm(
    workspace_id: int,
    branch_id: int,
    candidate_tuples: list[tuple[UASTNode, UASTNode, Path]],
    batch_size: int = 128,
    max_nodes: int | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> list[list[EnrichedNodeData]]:
    """Generates enriched node embeddings and summaries directly from AST without LLM calls.

    Extracts docstring/signature summaries for Neo4j and formats structured code representations
    for batch embedding via Voyage AI into Qdrant.

    Args:
        workspace_id (int): Target workspace ID.
        branch_id (int): Target branch ID.
        candidate_tuples (list[tuple[UASTNode, UASTNode, Path]]): List of (root_node, target_node, file_path).
        batch_size (int, optional): Number of nodes per embedding batch. Defaults to 128.
        max_nodes (int | None, optional): Optional limit on nodes to process. Defaults to None.
        vector_store (QdrantVectorStore | None, optional): Target QdrantVectorStore instance. Defaults to None.

    Returns:
        list[list[EnrichedNodeData]]: List of embedded node batches.
    """
    if not candidate_tuples:
        return []

    if max_nodes is not None and max_nodes > 0:
        candidate_tuples = candidate_tuples[:max_nodes]
        logger.info("Limited execution to first %d nodes.", len(candidate_tuples))

    qdrant_store = vector_store or QdrantVectorStore()
    all_embedded_batches: list[list[EnrichedNodeData]] = []
    total_nodes = len(candidate_tuples)

    logger.info(
        "Starting Zero-LLM Direct AST Embedding Pipeline | Total Nodes: %d | Batch Size: %d",
        total_nodes,
        batch_size,
    )

    batch_idx = 1
    total_batches = (total_nodes + batch_size - 1) // batch_size

    for chunk in chunk_list(candidate_tuples, batch_size):
        logger.info(
            "--- Batch %d/%d: Formatting & Embedding %d nodes (No LLM) ---",
            batch_idx,
            total_batches,
            len(chunk),
        )
        enhanced_batch: list[EnrichedNodeData] = []

        for root_node, target_node, file_path in chunk:
            signature = extract_node_signature(target_node)
            source_code = extract_source_code(root_node, target_node, file_path)
            scope_name = find_enclosing_scope_name(root_node, target_node)

            summary = extract_ast_summary(
                target_node=target_node,
                signature=signature,
                docstring=target_node.docstring,
                file_path=file_path,
                scope_name=scope_name,
            )

            formatted_embed_text = build_embed_text(
                file_path=str(file_path),
                scope_name=scope_name,
                node_type=target_node.node_type,
                symbol_name=target_node.name or "",
                signature=signature,
                docstring=target_node.docstring,
                code_snippet=source_code,
            )

            identifiers = extract_clean_identifiers(target_node)

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

        embedded_batch = batch_embed_nodes_template(
            enhanced_batch=enhanced_batch,
            vector_store=qdrant_store,
        )
        all_embedded_batches.append(embedded_batch)

        logger.info(
            "Batch %d/%d complete: %d nodes embedded with Voyage AI & saved to Qdrant.",
            batch_idx,
            total_batches,
            len(chunk),
        )
        batch_idx += 1

    return all_embedded_batches
