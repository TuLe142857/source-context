"""Hướng 2: FastAPI endpoints and requests/httpx calls from the CST, SCIP and imports."""

from collections.abc import Callable
import pytest
from tree_sitter import Node

from app.engine.api_map.handlers.api_handler import api_metadata
from app.engine.api_map import ApiMapContext
from app.engine.api_map.context import walk
from app.engine.api_map.languages.python.cst import evaluate, resolve_object
from app.engine.api_map.languages.python.rest_api import PythonRestApiHandler
from app.engine.graph.model import RestCallNodeModel, RestEndpointNodeModel

type MakeContext = Callable[
    ..., ApiMapContext
]  # the `make_ctx` fixture, see conftest.py


HANDLER = PythonRestApiHandler()

ENDPOINTS = {
    ("GET /health", "health"),
    ("GET /echo", "echo"),
    ("POST /echo", "echo"),
    ("GET /api/v1/users/{user_id}", "get_user"),
    ("POST /api/v1/users", "create_user"),
    ("DELETE /api/v1/users/{user_id}", "remove"),
    ("GET /api/v1/users/", "list_users"),
    ("PUT /api/v1/items/{item_id}", "update_item"),
}

CALLS = [
    ("DELETE", "http://users:8000/api/v1/users/1", "requests"),
    (
        "GET",
        None,
        "requests",
    ),  # requests.get(self.base + path) in the wrapper: unknown URL
    ("GET", "http://catalog:8000/api/v1/items/", "httpx"),
    ("GET", "http://catalog:8000/api/v1/products/{pid}", "requests"),
    ("GET", "http://users:8000/api/v1/users/{user_id}", "httpx"),
    ("PATCH", "http://billing:9000/api/{path}", "requests"),
    ("POST", "http://billing:9000/api/charge", "requests"),
]


def framework(ctx: ApiMapContext) -> list:
    return [
        (node, anchor)
        for node, anchor in HANDLER.detect_api(ctx)
        if api_metadata(node)["detector"] == "framework"
    ]


def anchored_name(
    ctx: ApiMapContext, anchor: tuple[str, int, int] | None
) -> str | None:
    if anchor is None:
        return None
    path, start, end = anchor
    return next(
        (
            n.name
            for n in walk(ctx.uast(path))
            if (n.start_byte, n.end_byte) == (start, end)
            and n.node_type in ("function", "call")
        ),
        None,
    )


@pytest.mark.parametrize("index", ["index.scip", "index_with_deps.scip"])
def test_fastapi_endpoints_with_prefixes_across_files(
    make_ctx: MakeContext, index: str
) -> None:
    """Same result with the production sandbox index (no fastapi installed) and a full one."""

    ctx = make_ctx(index)
    endpoints = [
        (n, a) for n, a in framework(ctx) if isinstance(n, RestEndpointNodeModel)
    ]

    assert {
        (node.signature, anchored_name(ctx, anchor)) for node, anchor in endpoints
    } == ENDPOINTS
    assert all(
        api_metadata(node)["mounted"] and api_metadata(node)["confidence"] == 0.95
        for node, _ in endpoints
    )


@pytest.mark.parametrize("index", ["index.scip", "index_with_deps.scip"])
def test_http_calls_with_base_urls(make_ctx: MakeContext, index: str) -> None:
    ctx = make_ctx(index)
    calls = [(n, a) for n, a in framework(ctx) if isinstance(n, RestCallNodeModel)]

    assert sorted(
        ((n.http_method, api_metadata(n)["url"], n.library) for n, _ in calls), key=str
    ) == sorted(CALLS, key=str)
    assert all(
        anchored_name(ctx, anchor) in ("get", "post", "delete", "request")
        for _, anchor in calls
    )


def test_call_fields(ctx: ApiMapContext) -> None:
    by_url = {
        api_metadata(n)["url"]: n
        for n, _ in framework(ctx)
        if isinstance(n, RestCallNodeModel)
    }

    fetch = by_url["http://users:8000/api/v1/users/{user_id}"]
    assert (fetch.target_hint, fetch.path, fetch.match_key) == (
        "http://users:8000",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{}",
    )
    assert fetch.is_dynamic and api_metadata(fetch)["scope"] == "UserClient.fetch"
    assert api_metadata(fetch)["base_url"] == '"http://users:8000/api/v1"'
    assert not by_url["http://billing:9000/api/charge"].is_dynamic


def test_without_scip_routes_lose_cross_file_prefixes(make_ctx: MakeContext) -> None:
    """Degraded mode: same-file resolution keeps every call, routers are no longer mounted."""

    ctx = make_ctx(None)
    detections = framework(ctx)
    endpoints = {
        n.signature: n for n, _ in detections if isinstance(n, RestEndpointNodeModel)
    }
    calls = sorted(
        (
            (n.http_method, api_metadata(n)["url"], n.library)
            for n, _ in detections
            if isinstance(n, RestCallNodeModel)
        ),
        key=str,
    )

    assert calls == sorted(CALLS, key=str)
    # routes on the app itself keep their full path and confidence
    assert api_metadata(endpoints["GET /health"])["confidence"] == 0.95
    unmounted = api_metadata(endpoints["GET /users/{user_id}"])
    assert (unmounted["mounted"], unmounted["confidence"]) == (False, 0.7)
    assert "PUT /{item_id}" in endpoints


def test_tier_a_reads_framework_symbols_only_when_installed(
    make_ctx: MakeContext,
) -> None:
    """``@router.get``: no occurrence for ``get`` without fastapi installed, a precise one with it."""

    def owner_of_router_get(ctx: ApiMapContext) -> str | None:
        path = "shop/routers/users.py"
        source = ctx.source(path)
        start = source.index(b"@router.get") + len(b"@router.")
        return ctx.scip_owner(path, start, start + len(b"get"))

    assert owner_of_router_get(make_ctx("index.scip")) is None
    assert (
        owner_of_router_get(make_ctx("index_with_deps.scip"))
        == "fastapi.routing.APIRouter()"
    )


def _find(ctx: ApiMapContext, path: str, needle: bytes, node_type: str) -> Node:
    start = ctx.source(path).index(needle)
    node = ctx.tree(path).root_node.descendant_for_byte_range(
        start, start + len(needle)
    )
    while node is not None and node.type != node_type:
        node = node.parent
    assert node is not None
    return node


def test_resolve_object_follows_project_names(ctx: ApiMapContext) -> None:
    main = "shop/main.py"
    include = _find(ctx, main, b"items_router, prefix", "call")
    alias = include.child_by_field_name("arguments").named_children[0]  # type: ignore[union-attr]

    kind, constructor, key = resolve_object(ctx, main, alias)

    assert (
        kind == "fastapi.APIRouter()"
    )  # `import fastapi; fastapi.APIRouter()` in items.py
    assert constructor is not None and constructor[0] == "shop/routers/items.py"
    assert key is not None and key.endswith("`shop.routers.items`/router.")


def test_evaluate_env_default_and_constants(ctx: ApiMapContext) -> None:
    path = "shop/clients/catalog.py"
    get_product = _find(ctx, path, b"requests.get(f", "call")
    url = get_product.child_by_field_name("arguments").named_children[0]  # type: ignore[union-attr]

    assert evaluate(ctx, path, url) == "http://catalog:8000/api/v1/products/{pid}"
