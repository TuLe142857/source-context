"""Detect the APIs of one project and store them.

Detection (``detect_apis``) is a pure function of the project's files, UAST and SCIP index;
only ``build_api_map_for_project`` touches Neo4j, through ``persist.save_detections``.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from app.engine.graph.model import ApiEndpointNodeModel, ApiNodeModel, ProjectNodeModel
from app.engine.parser.uast import ContainerNode, UASTNode
from app.engine.scip import scip_pb2 as scip
from app.engine.scip.index_reader import normalize_document_path, read_index

from .context import ApiMapContext
from .handlers.api_handler import ApiHandler, Detection, detection_confidence
from .persist import save_detections

logger = logging.getLogger(__name__)


def build_api_map_for_project(
    project_id: int,
    project_root: Path,
    index: scip.Index | None = None,
    file_roots: list[UASTNode] | None = None,
) -> dict[str, int]:
    """Detect the APIs of one project and replace its API nodes in Neo4j.

    Args:
        project_id: ``uid`` of the ``ProjectNodeModel`` whose UAST is already in Neo4j.
        project_root: Directory the file paths are relative to (``local_path / root_dir``).
        index: SCIP index of the project; ``None`` degrades to same-file resolution.
        file_roots: Stage-2 UAST roots of this run. Their ids are the Neo4j uids, so anchors
            resolve in memory and stale File nodes left by earlier runs are never picked up.
            Without them the project's files are read from Neo4j (CLI use).

    Returns:
        Counts per role and detector, for logging.
    """

    roots: dict[str, UASTNode] | None = None
    if file_roots is not None:
        roots = {
            normalize_document_path(root.path): root
            for root in file_roots
            if isinstance(root, ContainerNode) and root.path
        }
        file_uids = {path: root.id for path, root in roots.items()}
    else:
        file_uids = _file_uids_from_graph(project_id)

    ctx = ApiMapContext(
        project_id,
        project_root,
        file_uids,
        read_index(index) if index is not None else None,
        roots,
    )
    detections = detect_apis(ctx)
    save_detections(ctx, detections)
    summary = summarize(detections)
    logger.info("API map for project %s: %s", project_id, summary)
    return summary


def detect_apis(ctx: ApiMapContext) -> list[Detection]:
    """Run every registered handler on the languages of the project, then merge the results."""

    from .languages import (
        get_api_handler_registry,
    )  # import cycle: languages imports this package

    registry = get_api_handler_registry()
    handlers: list[ApiHandler] = []  # a handler serving several languages runs once
    for language in sorted(ctx.languages() & registry.languages()):
        for handler in registry.handlers_for(language):
            if handler not in handlers:
                handlers.append(handler)
    detections: list[Detection] = []
    for handler in handlers:
        detections += handler.detect_api(ctx)
    return merge_detections(detections)


def merge_detections(detections: list[Detection]) -> list[Detection]:
    """Framework detections win: a pattern detection whose anchor (for the same role) a framework
    detection already covers is dropped; duplicates by uid keep the most confident one."""

    covered = {
        (_role(node), anchor)
        for node, anchor in detections
        if anchor is not None and _detector(node) == "framework"
    }
    best: dict[str, Detection] = {}
    for node, anchor in detections:
        if _detector(node) != "framework" and (_role(node), anchor) in covered:
            continue
        kept = best.get(node.uid)
        if kept is None or detection_confidence(node) > detection_confidence(kept[0]):
            best[node.uid] = (node, anchor)
    return list(best.values())


def summarize(detections: list[Detection]) -> dict[str, int]:
    counts = Counter(f"{_role(node)}.{_detector(node)}" for node, _ in detections)
    counts["anchored"] = sum(anchor is not None for _, anchor in detections)
    return dict(sorted(counts.items()))


def _role(node: ApiNodeModel) -> str:
    return "endpoint" if isinstance(node, ApiEndpointNodeModel) else "call"


def _detector(node: ApiNodeModel) -> str:
    return str((node.metadata or {}).get("detector", ""))


def _file_uids_from_graph(project_id: int) -> dict[str, str]:
    """Relative path -> File uid. Re-indexing leaves older File nodes behind; the last one wins."""

    project: ProjectNodeModel = ProjectNodeModel.nodes.get(uid=project_id)
    file_uids: dict[str, str] = {}
    for file_node in project.files.all():
        if not file_node.relative_path:
            continue
        path = normalize_document_path(file_node.relative_path)
        if path in file_uids:
            logger.warning(
                "Several File nodes for %s in project %s, using one of them",
                path,
                project_id,
            )
        file_uids[path] = file_node.uid
    return file_uids
