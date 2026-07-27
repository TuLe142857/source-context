"""Utility functions for UAST node source extraction, signature extraction, identifier parsing, and structured embedding formatting."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Iterator

from app.parser.uast.node import (
    ContainerNode,
    FunctionNode,
    TypeDefinitionNode,
    UASTNode,
    VariableNode,
)

# Common non-semantic code stopwords to filter out from Identifiers
NOISE_STOPWORDS = {
    "dep",
    "col",
    "is",
    "in",
    "one",
    "all",
    "by",
    "at",
    "to",
    "or",
    "an",
    "if",
    "as",
    "do",
    "so",
    "my",
    "me",
    "we",
    "be",
    "on",
    "no",
    "self",
    "this",
    "none",
    "true",
    "false",
    "any",
    "str",
    "int",
    "dict",
    "list",
    "bool",
    "float",
    "val",
    "var",
    "def",
    "get",
    "set",
}


@dataclass(slots=True)
class EnrichedNodeData:
    """Enriched node metadata container ready for batch vector embedding."""

    node_id: str
    node_type: str
    kind: str
    name: str
    file_path: str
    signature: str
    source_code: str
    docstring: str | None
    summary: str | None = None
    identifiers: list[str] = field(default_factory=list)
    formatted_embed_text: str | None = None
    embedding: list[float] | None = None


def is_valid_docstring(docstring: str | None, node_name: str) -> bool:
    """Determines whether a docstring provides useful context or should be omitted.

    Omits docstrings that are None, too short (< 25 chars), or merely repeat the function name.
    """
    if not docstring or not docstring.strip():
        return False

    clean_doc = docstring.strip().strip('"').strip("'").strip()
    if len(clean_doc) < 25:
        return False

    # Check if docstring merely restates function name (e.g. "Retrieve items.", "Get item by ID.")
    clean_name_words = set(re.findall(r"\w+", node_name.lower()))
    clean_doc_words = set(re.findall(r"\w+", clean_doc.lower()))

    # If docstring adds less than 3 unique non-name words, omit it
    extra_words = clean_doc_words - clean_name_words - NOISE_STOPWORDS
    return len(extra_words) >= 3


def extract_source_code(
    root_node: UASTNode,
    target_node: UASTNode,
    file_path: str | Path,
) -> str:
    """Extracts the raw source code text of a target UAST node using byte offsets."""
    path = Path(file_path)
    source_bytes: bytes | None = None

    if isinstance(root_node, ContainerNode) and root_node.source_bytes:
        source_bytes = root_node.source_bytes
    elif path.exists() and path.is_file():
        source_bytes = path.read_bytes()

    if source_bytes is not None and target_node.end_byte > target_node.start_byte:
        extracted = source_bytes[target_node.start_byte : target_node.end_byte]
        return extracted.decode("utf-8", errors="replace")

    return f"# [Source code unavailable for {target_node.name}]"


def extract_function_signature(node: FunctionNode) -> str:
    """Extracts clean function signature string."""
    name = node.name or "unnamed_function"
    return_type = f" -> {node.return_type}" if node.return_type else ""
    async_prefix = "async " if node.is_async else ""

    parameters_lst: list[str] = []
    for child in node.children:
        if isinstance(child, VariableNode) and child.kind == "parameter":
            param_str = f"{child.name}: {child.data_type or 'Any'}"
            if child.initial_value:
                param_str += f" = {child.initial_value}"
            parameters_lst.append(param_str)

    params_str = ", ".join(parameters_lst)
    return f"{async_prefix}def {name}({params_str}){return_type}"


def extract_class_signature(node: TypeDefinitionNode) -> str:
    """Extracts clean class/type signature string."""
    name = node.name or "unnamed_class"
    base_types_str = f"({', '.join(node.base_types)})" if node.base_types else ""
    return f"class {name}{base_types_str}"


def extract_node_signature(node: UASTNode) -> str:
    """Routes signature extraction based on UAST node type."""
    if isinstance(node, FunctionNode):
        return extract_function_signature(node)
    elif isinstance(node, TypeDefinitionNode):
        return extract_class_signature(node)
    return f"construct {node.name or 'unnamed'}"


def extract_clean_identifiers(node: UASTNode) -> list[str]:
    """Extracts clean, split, deduplicated, non-stopword identifier tokens from node AST."""
    raw_tokens: set[str] = set()

    def _collect(n: UASTNode) -> None:
        if n.name:
            raw_tokens.add(n.name)
        if isinstance(n, VariableNode) and n.data_type:
            raw_tokens.add(n.data_type)
        if isinstance(n, FunctionNode) and n.return_type:
            raw_tokens.add(n.return_type)
        if isinstance(n, TypeDefinitionNode):
            for base in n.base_types:
                raw_tokens.add(base)

        for child in n.children:
            _collect(child)

    _collect(node)

    cleaned_terms: set[str] = set()
    for token in raw_tokens:
        split_token = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token).replace("_", " ")
        words = [w.strip().lower() for w in split_token.split() if w.strip()]

        filtered_words = [
            w
            for w in words
            if len(w) >= 2 and w not in NOISE_STOPWORDS and not w.isdigit()
        ]

        if filtered_words:
            if len(filtered_words) > 1:
                cleaned_terms.add(" ".join(filtered_words))
            for word in filtered_words:
                cleaned_terms.add(word)

    return sorted(cleaned_terms)


def format_node_for_embedding(
    node: UASTNode,
    summary: str,
    identifiers: list[str] | None = None,
) -> str:
    """Formats an enriched UAST node into a concise representation for vector embedding.

    Combines only the raw signature and clean AI summary, omitting template labels
    (Signature:, Summary:, Identifiers:), docstring duplication, and identifier lists
    to eliminate vector similarity degradation.
    """
    signature = extract_node_signature(node)
    clean_summary = summary.strip()
    return f"{signature}\n\n{clean_summary}"


# Alias for backward compatibility
extract_identifiers = extract_clean_identifiers


def extract_summarizable_nodes(root_node: UASTNode) -> list[UASTNode]:
    """Recursively traverses UAST tree and collects all FunctionNode and TypeDefinitionNode objects."""
    nodes: list[UASTNode] = []

    def _traverse(curr: UASTNode) -> None:
        if isinstance(curr, (FunctionNode, TypeDefinitionNode)):
            nodes.append(curr)
        for child in curr.children:
            _traverse(child)

    _traverse(root_node)
    return nodes


def chunk_list(items: list[Any], chunk_size: int) -> Iterator[list[Any]]:
    """Yields successive chunks of chunk_size from items list."""
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


IGNORE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".idea",
    ".pytest_cache",
    "build",
    "dist",
    "node_modules",
    ".gemini",
}


def scan_python_files(target_dir: Path) -> list[Path]:
    """Recursively scans a directory for Python files, skipping venv, git, and cache folders."""
    py_files: list[Path] = []
    if not target_dir.exists():
        return py_files

    if target_dir.is_file():
        if target_dir.suffix == ".py":
            py_files.append(target_dir)
        return py_files

    for path in target_dir.rglob("*.py"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file():
            py_files.append(path)

    return sorted(py_files)
