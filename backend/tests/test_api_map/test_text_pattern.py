"""Hướng 1: text-pattern rules over UAST nodes and source text."""

from collections.abc import Callable
from app.engine.api_map.handlers.api_handler import api_metadata
from app.engine.api_map import ApiMapContext, text_pattern
from app.engine.api_map.context import walk
from app.engine.api_map.languages.python.rest_api import PythonRestApiHandler
from app.engine.api_map.languages.python.rest_patterns import PYTHON_REST_PATTERNS
from app.engine.api_map.text_pattern import (
    call_arguments,
    evaluate_text,
    split_arguments,
)
from app.engine.graph.model import RestCallNodeModel, RestEndpointNodeModel

type MakeContext = Callable[
    ..., ApiMapContext
]  # the `make_ctx` fixture, see conftest.py


HANDLER = PythonRestApiHandler()


def detect(ctx: ApiMapContext) -> list:
    return text_pattern.detect(HANDLER, ctx, ctx.paths("python"), PYTHON_REST_PATTERNS)


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


def test_call_arguments_takes_the_last_top_level_parentheses() -> None:
    assert call_arguments('requests.get(f"{X}/a", timeout=5)') == 'f"{X}/a", timeout=5'
    assert call_arguments('get(x).get("/y")') == '"/y"'
    assert call_arguments('@router.get("/{user_id}")') == '"/{user_id}"'
    assert (
        call_arguments('c.post("/a)b", data={"k": (1, 2)})')
        == '"/a)b", data={"k": (1, 2)}'
    )
    assert call_arguments('c.get("""/x(""")') == '"""/x("""'


def test_split_and_evaluate_text() -> None:
    positional, keyword = split_arguments(
        '"/x", list_users, methods=["GET"], *rest', PYTHON_REST_PATTERNS
    )
    assert positional == ['"/x"', "list_users"]
    assert keyword == {"methods": '["GET"]'}

    constants = {"BASE": "http://billing:9000/api"}.get
    assert (
        evaluate_text('BASE + "/charge"', constants, PYTHON_REST_PATTERNS)
        == "http://billing:9000/api/charge"
    )
    assert (
        evaluate_text('f"{BASE}/u/{uid}"', constants, PYTHON_REST_PATTERNS)
        == "http://billing:9000/api/u/{uid}"
    )
    assert (
        evaluate_text('"/a/{b}"', constants, PYTHON_REST_PATTERNS) == "/a/{b}"
    )  # not an f-string
    assert (
        evaluate_text("self.base_url", constants, PYTHON_REST_PATTERNS) == "{base_url}"
    )
    assert evaluate_text("build_url()", constants, PYTHON_REST_PATTERNS) is None


def test_endpoints_from_decorators_and_add_route(ctx: ApiMapContext) -> None:
    endpoints = {
        (node.signature, anchored_name(ctx, anchor), api_metadata(node)["rule"])
        for node, anchor in detect(ctx)
        if isinstance(node, RestEndpointNodeModel)
    }

    assert endpoints == {
        ("GET /health", "health", "py.decorator.verb"),
        ("GET /echo", "echo", "py.decorator.route"),
        ("POST /echo", "echo", "py.decorator.route"),
        # same-file `APIRouter(prefix="/users")`, but not the include prefix of main.py
        ("GET /users/{user_id}", "get_user", "py.decorator.verb"),
        ("POST /users", "create_user", "py.decorator.verb"),
        ("DELETE /users/{user_id}", "remove", "py.decorator.verb"),
        ("GET /users/", "list_users", "py.call.add_route"),
        ("PUT /{item_id}", "update_item", "py.decorator.verb"),
    }


def test_calls(ctx: ApiMapContext) -> None:
    calls = sorted(
        (node.http_method, api_metadata(node)["url"], anchored_name(ctx, anchor))
        for node, anchor in detect(ctx)
        if isinstance(node, RestCallNodeModel)
    )

    assert calls == [
        ("DELETE", "http://users:8000/api/v1/users/1", "delete"),
        (
            "GET",
            "/api/v1/items/",
            "get",
        ),  # no base_url: text patterns do not follow the client
        ("GET", "/health", "get"),  # TestClient in tests/
        ("GET", "/orders", "get"),  # project wrapper, only the pattern detector sees it
        ("GET", "/users/{user_id}", "get"),
        # once: the outer `.json()` call starts with the same text but is not named `get`
        ("GET", "http://catalog:8000/api/v1/products/{pid}", "get"),
        ("PATCH", "http://billing:9000/api/{path}", "request"),
        ("POST", "http://billing:9000/api/charge", "post"),
    ]


def test_a_dict_get_that_looks_like_a_request_is_rejected(
    make_ctx: MakeContext,
) -> None:
    """``cache = {}; cache.get("/users/" + key)`` in a file importing requests.

    Two independent filters: the receiver's initial value (``{}``) and SCIP
    (``builtins/dict#get().``), so it is rejected with and without an index.
    """

    def cache_calls(ctx: ApiMapContext) -> list[str]:
        return [
            api_metadata(node)["url"]
            for node, _ in detect(ctx)
            if isinstance(node, RestCallNodeModel)
            and api_metadata(node)["scope"] == "cached_user"
        ]

    assert cache_calls(make_ctx("index.scip")) == []
    assert cache_calls(make_ctx(None)) == []


def test_framework_hint_and_confidence_bounds(ctx: ApiMapContext) -> None:
    for node, _ in detect(ctx):
        assert api_metadata(node)["detector"] == "pattern"
        assert 0.4 <= api_metadata(node)["confidence"] <= 0.8
        if isinstance(node, RestEndpointNodeModel):
            assert node.framework == "fastapi"
