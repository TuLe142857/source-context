"""Build a project's call graph from a SCIP index.

Every file's UAST tree is already in Neo4j when this runs; SCIP supplies the name
resolution Tree-sitter cannot do on its own. Joining the two is purely positional: a
SCIP occurrence covers an *identifier*, while a UAST reference node covers the *whole*
expression around it, so an occurrence belongs to the node whose byte span contains it
and whose ``name`` it matches.

Both sides are therefore grouped by identifier text, and the walk collects two things
per file:

* which UAST node declares each symbol, and
* which symbol each reference node points at.

The edges are created only once every file has been visited, because a reference may
well point at a definition in a file that has not been read yet.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from neomodel import db

from app.scip import scip_pb2 as scip
from app.scip.index_reader import SymbolOccurrence, SymbolTable, read_index
from app.scip.position import LineIndex

from .model import (
    DefinitionNodeModel,
    FileNodeModel,
    ProjectNodeModel,
    ReferenceNodeModel,
    UASTNodeModel,
)

logger = logging.getLogger(__name__)

type OccurrenceEntry = tuple[int, int, SymbolOccurrence]
"""An occurrence with its range resolved to ``(start_byte, end_byte, occurrence)``."""

type NodesByName = dict[str, list[UASTNodeModel]]
"""UAST nodes of one file, grouped by their ``name``."""

type OccurrencesByName = dict[str, list[OccurrenceEntry]]
"""Occurrences of one document, grouped by the identifier text they cover."""

_FILE_NODES_QUERY = """
MATCH (:File {uid: $file_uid})-[:DECLARE]->()-[:PARENT_OF*0..]->(n:Node)
RETURN DISTINCT n
"""
"""``DECLARE`` links a file only to its top-level nodes, so nested nodes are reached
through ``PARENT_OF``."""


def build_call_graph_for_project(
    project_id: int,
    index: scip.Index,
    project_root: Path,
) -> None:
    """Create ``REFERENCE_TO`` relations between the UAST nodes of one project.

    Args:
        project_id: ``uid`` of the ``ProjectNodeModel`` whose UAST is already in Neo4j.
        index: SCIP index covering the same project.
        project_root: Directory the SCIP document paths are relative to — the same
            ``local_path / root_dir`` the parsing stage walked.

    Returns:
        ``None``
    """

    project_node: ProjectNodeModel = ProjectNodeModel.nodes.get(uid=project_id)
    symbol_table = read_index(index)

    definition_by_symbol: dict[str, UASTNodeModel] = {}
    references: list[tuple[UASTNodeModel, str]] = []

    file_count = 0
    for nodes_by_name, occurrences_by_name in _iter_indexed_files(
        project_node, symbol_table, project_root
    ):
        file_count += 1
        _collect_definitions(nodes_by_name, occurrences_by_name, definition_by_symbol)
        _collect_references(nodes_by_name, occurrences_by_name, references)

    connected, external = _connect_references(references, definition_by_symbol)

    logger.info(
        "Call graph for project %s: %d files, %d definitions, %d references "
        "(%d connected, %d external)",
        project_id,
        file_count,
        len(definition_by_symbol),
        len(references),
        connected,
        external,
    )


def _iter_indexed_files(
    project_node: ProjectNodeModel,
    symbol_table: SymbolTable,
    project_root: Path,
) -> Iterator[tuple[NodesByName, OccurrencesByName]]:
    """Yield each project file's UAST nodes next to its SCIP occurrences.

    Both mappings are keyed by identifier text, which is what the matching relies on.
    Files the indexer did not cover, and files no longer readable on disk, are skipped —
    a partial graph is more useful than a failed build.

    Args:
        project_node: The project whose files are walked.
        symbol_table: Symbol table read from the SCIP index.
        project_root: Directory the document paths are relative to.

    Yields:
        ``(nodes_by_name, occurrences_by_name)`` for one file.
    """

    files: list[FileNodeModel] = project_node.files.all()
    for file_node in files:
        relative_path = _normalize_path(file_node.relative_path or "")

        occurrences = symbol_table.occurrences_by_document.get(relative_path)
        if occurrences is None:
            logger.debug("No SCIP document for %s, skipping", relative_path)
            continue

        try:
            source = (project_root / relative_path).read_bytes()
        except OSError:
            logger.warning("Cannot read %s, skipping", relative_path)
            continue

        yield (
            _group_nodes_by_name(_load_file_nodes(file_node)),
            _group_occurrences_by_name(occurrences, LineIndex(source), relative_path),
        )


def _normalize_path(relative_path: str) -> str:
    """Bring a stored path into the form SCIP uses: ``/`` separators, no ``./`` prefix.

    Args:
        relative_path: Path as stored on ``FileNodeModel``.

    Returns:
        The normalized path.
    """

    return relative_path.replace("\\", "/").removeprefix("./")


def _load_file_nodes(file_node: FileNodeModel) -> list[UASTNodeModel]:
    """Load every UAST node of one file, nested ones included.

    Args:
        file_node: The file to load.

    Returns:
        The file's nodes, each inflated to its concrete model class.
    """

    rows: list[list[Any]]
    rows, _ = db.cypher_query(
        _FILE_NODES_QUERY, {"file_uid": file_node.uid}, resolve_objects=True
    )
    return [row[0] for row in rows]


def _group_nodes_by_name(nodes: list[UASTNodeModel]) -> NodesByName:
    """Group UAST nodes by ``name``, dropping the unnamed ones.

    Args:
        nodes: Nodes of a single file.

    Returns:
        Identifier text -> the nodes carrying it.
    """

    grouped: NodesByName = defaultdict(list)
    for node in nodes:
        if node.name:
            grouped[node.name].append(node)
    return grouped


def _group_occurrences_by_name(
    occurrences: list[SymbolOccurrence],
    line_index: LineIndex,
    relative_path: str,
) -> OccurrencesByName:
    """Resolve every occurrence range to byte offsets and group by identifier text.

    SCIP counts characters from the start of a line while the UAST carries Tree-sitter
    byte offsets; the two only agree on pure ASCII, so the conversion always goes
    through ``LineIndex``.

    Args:
        occurrences: Occurrences the index reports for this document.
        line_index: Line table of the document's source.
        relative_path: Document path, used for logging.

    Returns:
        Identifier text -> the occurrences covering it.
    """

    grouped: OccurrencesByName = defaultdict(list)
    for occurrence in occurrences:
        try:
            start_byte, end_byte = line_index.range_to_bytes(occurrence.scip_range)
        except ValueError:
            logger.warning(
                "Malformed SCIP range %s in %s", occurrence.scip_range, relative_path
            )
            continue

        name = line_index.slice_text(start_byte, end_byte)
        if name:
            grouped[name].append((start_byte, end_byte, occurrence))
    return grouped


def _collect_definitions(
    nodes_by_name: NodesByName,
    occurrences_by_name: OccurrencesByName,
    definition_by_symbol: dict[str, UASTNodeModel],
) -> None:
    """Record which UAST node declares each symbol defined in this file.

    Args:
        nodes_by_name: The file's UAST nodes.
        occurrences_by_name: The file's occurrences.
        definition_by_symbol: Accumulator, updated in place.

    Returns:
        ``None``
    """

    for name, entries in occurrences_by_name.items():
        for start_byte, end_byte, occurrence in entries:
            if not occurrence.is_definition:
                continue

            node = _innermost_node_containing(
                nodes_by_name.get(name, []), start_byte, end_byte
            )
            if node is not None:
                # First definition wins: conditional definitions and @overload
                # legitimately produce several sites for one symbol.
                definition_by_symbol.setdefault(occurrence.symbol, node)


def _collect_references(
    nodes_by_name: NodesByName,
    occurrences_by_name: OccurrencesByName,
    references: list[tuple[UASTNodeModel, str]],
) -> None:
    """Record which symbol each reference node of this file points at.

    Args:
        nodes_by_name: The file's UAST nodes.
        occurrences_by_name: The file's occurrences.
        references: Accumulator of ``(reference node, symbol)``, updated in place.

    Returns:
        ``None``
    """

    for name, nodes in nodes_by_name.items():
        entries = occurrences_by_name.get(name)
        if not entries:
            continue

        for node in nodes:
            if not isinstance(node, ReferenceNodeModel):
                continue

            occurrence = _occurrence_inside(node, entries)
            if occurrence is not None:
                references.append((node, occurrence.symbol))


def _innermost_node_containing(
    nodes: list[UASTNodeModel], start_byte: int, end_byte: int
) -> UASTNodeModel | None:
    """Smallest node covering the given span, declarations preferred.

    A definition identifier sits inside every enclosing node — a method's name is inside
    both its class node and its function node — so the innermost match is the one that
    actually declares it.

    Args:
        nodes: Candidates, already filtered to those carrying the right name.
        start_byte: Inclusive start of the identifier span.
        end_byte: Exclusive end of the identifier span.

    Returns:
        The declaring node, or ``None`` when no candidate covers the span.
    """

    candidates = [
        node
        for node in nodes
        if node.start_byte <= start_byte and end_byte <= node.end_byte
    ]
    if not candidates:
        return None

    definitions = [node for node in candidates if isinstance(node, DefinitionNodeModel)]
    return min(
        definitions or candidates, key=lambda node: node.end_byte - node.start_byte
    )


def _occurrence_inside(
    node: UASTNodeModel, entries: list[OccurrenceEntry]
) -> SymbolOccurrence | None:
    """First non-definition occurrence covered by ``node``.

    A reference node spans a whole expression (``CallNode`` for ``g.greet()`` starts at
    ``g``) while an occurrence covers only the identifier, so containment — not
    equality — is what links the two. Definition occurrences are excluded: ``self.name``
    in ``self.name = name`` *is* the definition site, and linking it would produce a
    self-loop.

    Args:
        node: The reference node being resolved.
        entries: Occurrences carrying the same identifier text as ``node``.

    Returns:
        The matching occurrence, or ``None`` when the index has none.
    """

    for start_byte, end_byte, occurrence in entries:
        if occurrence.is_definition:
            continue
        if node.start_byte <= start_byte and end_byte <= node.end_byte:
            return occurrence
    return None


def _connect_references(
    references: list[tuple[UASTNodeModel, str]],
    definition_by_symbol: dict[str, UASTNodeModel],
) -> tuple[int, int]:
    """Create the ``REFERENCE_TO`` relations.

    Symbols without a definition site anywhere in the index are defined outside the
    project — the standard library and third-party packages — and are skipped.

    Args:
        references: ``(reference node, symbol)`` pairs collected from every file.
        definition_by_symbol: Where each symbol is declared.

    Returns:
        How many relations were created, and how many references were external.
    """

    connected = 0
    external = 0

    for node, symbol in references:
        target = definition_by_symbol.get(symbol)
        if target is None:
            external += 1
            continue
        if target.uid == node.uid:
            continue

        node.references.connect(target)
        connected += 1

    return connected, external
