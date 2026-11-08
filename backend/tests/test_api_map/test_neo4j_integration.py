"""End to end on Neo4j: stage-2 UAST saved, API map built as the pipeline does, then linked.

The Python sample is split into a server project (``shop/main.py`` + ``shop/routers``) and a
client project (``shop/clients``); the JS/TS sample already is two projects. Skipped when Neo4j is not reachable. Uses its own project uids and
deletes everything it wrote.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from neomodel import db, get_config

from app.core.config import settings
from app.engine.api_map import build_api_map_for_project, link_api_map
from app.engine.graph import save_file_node
from app.engine.graph.model import ProjectNodeModel
from app.engine.parser.languages import get_language_registry
from app.engine.parser.uast import UASTNode
from app.engine.scip import scip_pb2

pytestmark = pytest.mark.integration

SAMPLE = Path(__file__).parent / "fixtures" / "fastapi_sample"
EXPRESS = Path(__file__).parent / "fixtures" / "express_sample"
SERVER, CLIENT = 990_000_001, 990_000_002
JS_SERVER, JS_CLIENT = 990_000_003, 990_000_004
IDS = [SERVER, CLIENT, JS_SERVER, JS_CLIENT]

_CLEANUP = """
MATCH (p:Project) WHERE p.uid IN $ids
OPTIONAL MATCH (p)-[:INCLUDES]->(f:File)
OPTIONAL MATCH (f)-[:DECLARE]->()-[:PARENT_OF*0..]->(n:Node)
OPTIONAL MATCH (a:Api) WHERE a.project_id IN $ids
DETACH DELETE p, f, n, a
"""


@pytest.fixture(scope="module")
def neo4j() -> Iterator[None]:
    get_config().database_url = settings.NEO4J_URI
    try:
        db.cypher_query("RETURN 1")
    except Exception as exc:  # noqa: BLE001 - any connection problem means "no database here"
        pytest.skip(f"Neo4j not reachable: {exc}")
    db.cypher_query(_CLEANUP, {"ids": IDS})
    yield
    db.cypher_query(_CLEANUP, {"ids": IDS})


def _index(root: Path = SAMPLE) -> scip_pb2.Index:
    index = scip_pb2.Index()
    index.ParseFromString((root / "index.scip").read_bytes())
    return index


def _stage2(
    project_id: int, prefixes: tuple[str, ...], root_dir: Path = SAMPLE
) -> list[UASTNode]:
    """What parse_tree_sitter_ast_stage does: parse, save to Neo4j (no S3 upload), keep the roots."""

    ProjectNodeModel(uid=project_id).save()
    registry = get_language_registry()
    roots = []
    for file in sorted(root_dir.rglob("*")):
        if file.suffix not in (".py", ".ts", ".js"):
            continue
        relative = str(file.relative_to(root_dir))
        if not relative.startswith(prefixes):
            continue
        source = file.read_bytes()
        tree = registry.get_parser_for_file(file.name).parse(source)
        root = registry.get_converter_for_file(file.name).convert(
            tree, source, relative
        )
        save_file_node(root, project_id)
        roots.append(root)
    return roots


def _build(
    project_id: int, roots: list[UASTNode], root_dir: Path = SAMPLE
) -> dict[str, int]:
    return build_api_map_for_project(
        project_id, root_dir, index=_index(root_dir), file_roots=roots
    )


def test_build_anchor_and_link(neo4j: None) -> None:
    server_roots = _stage2(SERVER, ("shop/main.py", "shop/routers"))
    client_roots = _stage2(CLIENT, ("shop/clients",))

    assert _build(SERVER, server_roots)["endpoint.framework"] == 8
    assert _build(CLIENT, client_roots)["call.framework"] == 7

    # every endpoint hangs on its handler Function, every framework call on its Call node
    rows, _ = db.cypher_query(
        """
        MATCH (:Project {uid: $server})-[:EXPOSES_API]->(e:RestEndpoint)
        OPTIONAL MATCH (f:Function)-[:HANDLES_API]->(e)
        RETURN e.signature, f.name ORDER BY e.signature
        """,
        {"server": SERVER},
    )
    assert dict(rows) == {
        "DELETE /api/v1/users/{user_id}": "remove",
        "GET /api/v1/users/": "list_users",
        "GET /api/v1/users/{user_id}": "get_user",
        "GET /echo": "echo",
        "GET /health": "health",
        "POST /api/v1/users": "create_user",
        "POST /echo": "echo",
        "PUT /api/v1/items/{item_id}": "update_item",
    }
    rows, _ = db.cypher_query(
        """
        MATCH (:Project {uid: $client})-[:HAS_API_CALL]->(c:RestCall)
        OPTIONAL MATCH (n:Call)-[:MAKES_API_CALL]->(c)
        RETURN count(c), count(n)
        """,
        {"client": CLIENT},
    )
    assert (
        rows[0][0] == rows[0][1] == 8
    )  # 7 framework calls + the wrapper call found by pattern

    assert link_api_map([SERVER, CLIENT]) >= 2
    rows, _ = db.cypher_query(
        """
        MATCH (c:RestCall)-[r:RESOLVES_TO]->(e:RestEndpoint)
        WHERE c.project_id = $client AND e.project_id = $server
        RETURN c.signature, e.signature, r.rule, r.confidence ORDER BY c.signature
        """,
        {"client": CLIENT, "server": SERVER},
    )
    links = {(call, endpoint, rule) for call, endpoint, rule, _ in rows}
    assert (
        "GET /api/v1/users/{user_id}",
        "GET /api/v1/users/{user_id}",
        "exact",
    ) in links
    assert (
        "DELETE /api/v1/users/1",
        "DELETE /api/v1/users/{user_id}",
        "pattern",
    ) in links
    assert all(0 < confidence <= 1 for *_, confidence in rows)
    # GET /api/v1/items/ must not reach PUT /api/v1/items/{item_id}: other method, other length
    assert not any(call == "GET /api/v1/items/" for call, _, _ in links)

    # re-running replaces the nodes: same uids, no duplicates, links recomputed
    _build(SERVER, server_roots)
    rows, _ = db.cypher_query(
        "MATCH (a:Api) WHERE a.project_id = $server RETURN count(a)", {"server": SERVER}
    )
    assert rows[0][0] == 8
    assert link_api_map([SERVER, CLIENT]) == len(links)


def test_javascript_projects_build_anchor_and_link(neo4j: None) -> None:
    server, client = EXPRESS / "server", EXPRESS / "client"
    server_roots = _stage2(JS_SERVER, ("src",), server)
    client_roots = _stage2(JS_CLIENT, ("src",), client)

    assert _build(JS_SERVER, server_roots, server)["endpoint.framework"] == 10
    assert _build(JS_CLIENT, client_roots, client)["call.framework"] == 6

    # named handlers hang on their Function, inline arrow handlers on the registering Call
    rows, _ = db.cypher_query(
        """
        MATCH (:Project {uid: $server})-[:EXPOSES_API]->(e:RestEndpoint)
        MATCH (n:Node)-[:HANDLES_API]->(e)
        RETURN e.signature, labels(n), n.name
        """,
        {"server": JS_SERVER},
    )
    anchors = {
        sig: ("Function" if "Function" in labels else "Call", name)
        for sig, labels, name in rows
    }
    assert len(anchors) == 10
    assert anchors["GET /api/v1/products"] == ("Function", "listProducts")
    assert anchors["PUT /api/v1/orders/:orderId/status"] == ("Function", "updateStatus")
    assert anchors["GET /api/accounts/:id"] == ("Function", "findOne")
    assert anchors["GET /health"] == ("Call", "get")

    assert link_api_map([JS_SERVER, JS_CLIENT]) == 5
    rows, _ = db.cypher_query(
        """
        MATCH (c:RestCall)-[r:RESOLVES_TO]->(e:RestEndpoint)
        WHERE c.project_id = $client AND e.project_id = $server
        RETURN c.signature, e.signature, r.rule
        """,
        {"client": JS_CLIENT, "server": JS_SERVER},
    )
    assert ("GET /api/v1/users/{id}", "GET /api/v1/users/:id", "exact") in {
        tuple(r) for r in rows
    }
    assert all(rule == "exact" for *_, rule in rows)


def test_list_project_endpoints_and_calls(neo4j: None) -> None:
    """The read side behind ``GET /mcp/v1/api-map/projects/{id}/endpoints|calls``."""

    from unittest.mock import MagicMock

    from app.core import AppException
    from app.engine.graph.service import GraphService

    graph_service = GraphService(MagicMock())  # S3 is not used by the API map

    # earlier tests of this module already created these projects
    db.cypher_query(_CLEANUP, {"ids": IDS})
    server_roots = _stage2(SERVER, ("shop/main.py", "shop/routers"))
    client_roots = _stage2(CLIENT, ("shop/clients",))
    _build(SERVER, server_roots)
    _build(CLIENT, client_roots)
    link_api_map([SERVER, CLIENT])

    endpoints = graph_service.list_api_endpoints_in_project(SERVER)
    assert len(endpoints) == 8
    get_user = next(
        e for e in endpoints if e["signature"] == "GET /api/v1/users/{user_id}"
    )
    assert get_user["protocol"] == "rest"
    assert get_user["details"] == {
        "http_method": "GET",
        "path": "/api/v1/users/{user_id}",
        "path_params": ["user_id"],
    }
    assert get_user["handler_name"] == "get_user"
    assert get_user["handler_node_id"] is not None
    assert get_user["file_path"] == "shop/routers/users.py"
    assert get_user["start_line"] >= 1
    assert get_user["caller_count"] >= 1
    assert get_user["metadata"]["detector"] == "framework"

    calls = graph_service.list_api_calls_in_project(CLIENT)
    assert len(calls) == 8
    assert all(c["call_node_id"] is not None for c in calls)
    assert [(c["file_path"], c["start_line"]) for c in calls] == sorted(
        (c["file_path"], c["start_line"]) for c in calls
    )
    delete = next(c for c in calls if c["signature"] == "DELETE /api/v1/users/1")
    assert delete["details"] == {"http_method": "DELETE", "path": "/api/v1/users/1"}
    assert [(t["signature"], t["rule"]) for t in delete["targets"]] == [
        ("DELETE /api/v1/users/{user_id}", "pattern")
    ]
    assert delete["targets"][0]["project_id"] == SERVER

    with pytest.raises(AppException):
        graph_service.list_api_endpoints_in_project(990_999_999)
