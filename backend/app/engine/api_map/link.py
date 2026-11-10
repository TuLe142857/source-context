"""Link API calls to the endpoints they reach (``RESOLVES_TO``), across the projects of a workspace."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any

from neomodel import db

from app.engine.graph.model import ApiCallNodeModel, ApiEndpointNodeModel

logger = logging.getLogger(__name__)

_LOAD = "MATCH (a:Api) WHERE a.project_id IN $project_ids RETURN a"
_CLEAR = (
    "MATCH (c:ApiCall)-[r:RESOLVES_TO]->() WHERE c.project_id IN $project_ids DELETE r"
)
_CREATE = """
UNWIND $rows AS row
MATCH (c:ApiCall {uid: row.call})
MATCH (e:ApiEndpoint {uid: row.endpoint})
MERGE (c)-[r:RESOLVES_TO]->(e)
SET r.rule = row.rule, r.confidence = row.confidence
"""


def link_api_map(project_ids: Sequence[int], include_tests: bool = False) -> int:
    """Recompute every ``RESOLVES_TO`` of the calls of ``project_ids``.

    Both ends stay inside ``project_ids``, the projects of one workspace. Calls from test files
    hit the app under test and are skipped unless ``include_tests``.

    Returns:
        How many relations were created.
    """

    from .languages import (
        get_api_handler_registry,
    )  # import cycle: languages imports this package

    ids = list(project_ids)
    if not ids:
        return 0
    rows, _ = db.cypher_query(_LOAD, {"project_ids": ids}, resolve_objects=True)
    endpoints: dict[str, list[ApiEndpointNodeModel]] = defaultdict(list)
    calls: dict[str, list[ApiCallNodeModel]] = defaultdict(list)
    for (node,) in rows:
        if isinstance(node, ApiEndpointNodeModel):
            endpoints[node.protocol].append(node)
        elif isinstance(node, ApiCallNodeModel):
            calls[node.protocol].append(node)

    registry = get_api_handler_registry()
    links: list[dict[str, Any]] = []
    for protocol, protocol_calls in calls.items():
        matcher = registry.matcher(protocol)
        if matcher is None:
            continue
        for call in protocol_calls:
            if not include_tests and (call.metadata or {}).get("in_test"):
                continue
            for endpoint, rule, confidence in matcher.resolve_call(
                call, endpoints[protocol]
            ):
                links.append(
                    {
                        "call": call.uid,
                        "endpoint": endpoint.uid,
                        "rule": rule,
                        "confidence": confidence,
                    }
                )

    with db.transaction:
        db.cypher_query(_CLEAR, {"project_ids": ids})
        if links:
            db.cypher_query(_CREATE, {"rows": links})
    logger.info(
        "API links for projects %s: %d (%s)",
        ids,
        len(links),
        dict(Counter(link["rule"] for link in links)),
    )
    return len(links)
