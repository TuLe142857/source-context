"""Backward compatibility exports for embedding enhancer module."""

from app.embedding.embedding_pipeline import (
    batch_embed_nodes_template,
    parse_and_convert_file,
    run_embedding_pipeline,
)
from app.embedding.inference import get_openai_client, get_summary
from app.embedding.utils import (
    EnrichedNodeData,
    chunk_list,
    extract_class_signature,
    extract_function_signature,
    extract_identifiers,
    extract_node_signature,
    extract_source_code,
    extract_summarizable_nodes,
    format_node_for_embedding,
    scan_python_files,
)

__all__ = [
    "EnrichedNodeData",
    "batch_embed_nodes_template",
    "chunk_list",
    "extract_class_signature",
    "extract_function_signature",
    "extract_identifiers",
    "extract_node_signature",
    "extract_source_code",
    "extract_summarizable_nodes",
    "format_node_for_embedding",
    "get_openai_client",
    "get_summary",
    "parse_and_convert_file",
    "run_embedding_pipeline",
    "scan_python_files",
]
