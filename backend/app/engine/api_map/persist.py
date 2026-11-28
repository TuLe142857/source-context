"""Store detected API nodes in Neo4j and anchor them on their UAST nodes."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from neomodel import db

from app.engine.graph.model import ApiEndpointNodeModel

from .context import ApiMapContext, walk
from .handlers.api_handler import Detection

logger = logging.getLogger(__name__)

type AnchorKey = tuple[str, int, int, str]
"""``(path, start_byte, end_byte, node_type)``: endpoints hang on ``function``, calls on ``call``."""

_DELETE = "MATCH (a:Api {project_id: $project_id}) DETACH DELETE a"

_OWN = """
MATCH (p:Project {uid: $project_id})
UNWIND $rows AS row
MATCH (a:Api {uid: row.api})
MERGE (p)-[:%s]->(a)
"""

_ANCHOR = """
UNWIND $rows AS row
MATCH (n:Node {uid: row.node})
MATCH (a:Api {uid: row.api})
MERGE (n)-[:%s]->(a)
"""

_FILE_ANCHORS = """
MATCH (:File {uid: $file_uid})-[:DECLARE]->()-[:PARENT_OF*0..]->(n:Node)
WHERE n:Function OR n:Call
RETURN DISTINCT n.uid, n.start_byte, n.end_byte, n.node_type
"""


def save_detections(ctx: ApiMapContext, detections: list[Detection]) -> None:
    """Replace the project's API nodes, then connect them to the project and to their anchors.

    API uids are deterministic, so deleting and recreating keeps them stable while dropping
    endpoints removed from the code and anchors left on UAST nodes of an earlier run. Calls of
    other projects lose their ``RESOLVES_TO`` to this project's endpoints: the workspace linking
    step must run afterwards.
    """

    anchor_uids = _anchor_uids(ctx, detections)
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unanchored = 0
    with db.transaction:
        db.cypher_query(_DELETE, {"project_id": ctx.project_id})
        for node, anchor in detections:
            node.save()
            endpoint = isinstance(node, ApiEndpointNodeModel)
            rows["EXPOSES_API" if endpoint else "HAS_API_CALL"].append(
                {"api": node.uid}
            )
            node_uid = None
            if anchor is not None:
                # an inline handler (`app.get("/x", (req, res) => ...)`) is no UAST Function:
                # the endpoint then hangs on the Call registering the route
                for node_type in ("function", "call") if endpoint else ("call",):
                    node_uid = node_uid or anchor_uids.get((*anchor, node_type))
            if node_uid is None:
                unanchored += 1
                continue
            rows["HANDLES_API" if endpoint else "MAKES_API_CALL"].append(
                {"api": node.uid, "node": node_uid}
            )
        for rel in ("EXPOSES_API", "HAS_API_CALL"):
            if rows[rel]:
                db.cypher_query(
                    _OWN % rel, {"project_id": ctx.project_id, "rows": rows[rel]}
                )
        for rel in ("HANDLES_API", "MAKES_API_CALL"):
            if rows[rel]:
                db.cypher_query(_ANCHOR % rel, {"rows": rows[rel]})
    if unanchored:
        logger.info(
            "Project %s: %d API nodes without a UAST anchor", ctx.project_id, unanchored
        )


def _anchor_uids(
    ctx: ApiMapContext, detections: list[Detection]
) -> dict[AnchorKey, str]:
    """UAST uid of every anchor: from the stage-2 roots when the pipeline passed them (their ids
    are the Neo4j uids), else from the graph, one query per anchored file."""

    paths = {anchor[0] for _, anchor in detections if anchor is not None}
    result: dict[AnchorKey, str] = {}
    for path in paths:
        root = ctx.persisted_root(path)
        if root is not None:
            for node in walk(root):
                if node.node_type in ("function", "call"):
                    result.setdefault(
                        (path, node.start_byte, node.end_byte, node.node_type), node.id
                    )
            continue
        file_uid = ctx.file_uids.get(path)
        if file_uid is None:
            continue
        rows, _ = db.cypher_query(_FILE_ANCHORS, {"file_uid": file_uid})
        for uid, start_byte, end_byte, node_type in rows:
            result.setdefault((path, start_byte, end_byte, node_type), uid)
    return result
