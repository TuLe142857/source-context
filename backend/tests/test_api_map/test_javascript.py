"""JavaScript / TypeScript: Express, NestJS, axios and fetch, both approaches, and linking."""

from collections.abc import Callable

import pytest

from app.engine.api_map import ApiMapContext, detect_apis, text_pattern
from app.engine.api_map.context import walk
from app.engine.api_map.handlers.api_handler import Anchor, api_metadata
from app.engine.api_map.languages.javascript.rest_api import JavascriptRestApiHandler
from app.engine.api_map.languages.javascript.rest_patterns import (
    JAVASCRIPT_REST_PATTERNS,
)
from app.engine.graph.model import (
    ApiEndpointNodeModel,
    RestCallNodeModel,
    RestEndpointNodeModel,
)

type MakeJsContext = Callable[
    ..., ApiMapContext
]  # the `make_js_ctx` fixture, see conftest.py

HANDLER = JavascriptRestApiHandler()

SERVER_ENDPOINTS = {
    # (signature, UAST node it hangs on: function name, or the registering call's name)
    ("GET /health", "call:get"),  # inline handler -> the `app.get(...)` call
    (
        "GET /api/v1/products",
        "function:listProducts",
    ),  # app.route(...).get(listProducts)
    ("POST /api/v1/products", "call:post"),
    (
        "GET /api/v1/users/:id",
        "call:get",
    ),  # app.use(`${API_PREFIX}/users`, usersRouter)
    ("POST /api/v1/users/", "function:createUser"),
    ("DELETE /api/v1/users/:id", "call:delete"),
    ("GET /api/v1/orders/:orderId", "call:get"),  # default import of `router`
    (
        "PUT /api/v1/orders/:orderId/status",
        "function:updateStatus",
    ),  # const updateStatus = (...) =>
    (
        "GET /api/accounts/:id",
        "function:findOne",
    ),  # setGlobalPrefix("api") + @Controller + @Get
    ("POST /api/accounts", "function:create"),
}

CLIENT_CALLS = {
    (
        "GET",
        "http://users:3000/api/v1/users/{id}",
        "axios",
    ),  # axios.create({ baseURL })
    ("POST", "http://users:3000/api/v1/orders", "axios"),
    (
        "PUT",
        "http://users:3000/api/v1/orders/{orderId}/status",
        "fetch",
    ),  # fetch(url, { method })
    (
        "DELETE",
        "http://users:3000/api/v1/users/{id}",
        "axios",
    ),  # axios({ method, url })
    ("GET", "/api/accounts/{id}", "fetch"),
    (
        "GET",
        "http://users:3000/api/v1/products",
        "axios",
    ),  # this.client, require("axios")
}


def anchored(ctx: ApiMapContext, anchor: Anchor | None) -> str | None:
    if anchor is None:
        return None
    path, start, end = anchor
    by_type = {
        node.node_type: node.name
        for node in walk(ctx.uast(path))
        if (node.start_byte, node.end_byte) == (start, end)
    }
    for node_type in ("function", "call"):
        if node_type in by_type:
            return f"{node_type}:{by_type[node_type]}"
    return None


def framework(ctx: ApiMapContext) -> list:
    return [
        (node, anchor)
        for node, anchor in HANDLER.detect_api(ctx)
        if api_metadata(node)["detector"] == "framework"
    ]


def test_handler_serves_the_whole_family() -> None:
    assert HANDLER.languages == ("javascript", "typescript", "tsx")


def test_express_and_nest_endpoints(make_js_ctx: MakeJsContext) -> None:
    ctx = make_js_ctx("server")
    endpoints = [
        (n, a) for n, a in framework(ctx) if isinstance(n, RestEndpointNodeModel)
    ]

    assert {
        (node.signature, anchored(ctx, anchor)) for node, anchor in endpoints
    } == SERVER_ENDPOINTS
    by_signature = {node.signature: node for node, _ in endpoints}
    assert by_signature["GET /api/v1/users/:id"].match_key == "/api/v1/users/{}"
    assert by_signature["GET /api/v1/users/:id"].path_params == ["id"]
    assert by_signature["GET /api/accounts/:id"].framework == "nestjs"
    assert all(api_metadata(n)["confidence"] >= 0.9 for n, _ in endpoints)


def test_client_calls_with_base_urls(make_js_ctx: MakeJsContext) -> None:
    ctx = make_js_ctx("client")
    calls = [n for n, _ in framework(ctx) if isinstance(n, RestCallNodeModel)]

    assert {
        (n.http_method, api_metadata(n)["url"], n.library) for n in calls
    } == CLIENT_CALLS
    # `cache = new Map(); cache.get("/users/...")` is not a request
    assert not any(api_metadata(n)["scope"] == "cached" for n in calls)


@pytest.mark.parametrize("project", ["server", "client"])
def test_without_scip_calls_stay_whole_and_routers_lose_their_mount(
    make_js_ctx: MakeJsContext, project: str
) -> None:
    ctx = make_js_ctx(project, index=False)
    detections = framework(ctx)

    if project == "client":
        calls = {
            (n.http_method, api_metadata(n)["url"], n.library) for n, _ in detections
        }
        assert calls == CLIENT_CALLS
        return
    signatures = {n.signature: api_metadata(n) for n, _ in detections}
    assert signatures["GET /health"]["confidence"] == 0.95  # on the app itself
    assert (
        signatures["GET /api/accounts/:id"]["confidence"] == 0.9
    )  # same-file Nest wiring
    assert (
        signatures["GET /:id"]["mounted"],
        signatures["GET /:id"]["confidence"],
    ) == (False, 0.7)


def test_text_patterns(make_js_ctx: MakeJsContext) -> None:
    server, client = make_js_ctx("server"), make_js_ctx("client")

    def found(ctx: ApiMapContext) -> set[tuple[str, str]]:
        return {
            (node.signature or "", api_metadata(node)["rule"])
            for node, _ in text_pattern.detect(
                HANDLER, ctx, sorted(ctx.file_uids), JAVASCRIPT_REST_PATTERNS
            )
        }

    assert found(server) == {
        ("GET /health", "js.call.route"),
        ("GET /:id", "js.call.route"),  # no cross-file mount prefix in text patterns
        ("POST /", "js.call.route"),
        ("DELETE /:id", "js.call.route"),
        ("GET /:orderId", "js.call.route"),
        ("PUT /:orderId/status", "js.call.route"),
        (
            "GET /accounts/:id",
            "js.decorator.nest",
        ),  # @Controller prefix, no global prefix
        ("POST /accounts", "js.decorator.nest"),
    }
    assert found(client) == {
        ("GET /users/{id}", "js.call.verb"),  # no baseURL
        ("POST /api/v1/orders", "js.call.verb"),
        ("PUT /api/v1/orders/{orderId}/status", "js.call.fetch"),
        ("DELETE /api/v1/users/{id}", "js.call.config"),
        ("GET /api/accounts/{id}", "js.call.fetch"),
        ("GET /products", "js.call.verb"),
    }


def test_detect_apis_keeps_framework_results(make_js_ctx: MakeJsContext) -> None:
    detections = detect_apis(make_js_ctx("server"))

    assert len(detections) == len(SERVER_ENDPOINTS)
    assert {api_metadata(n)["detector"] for n, _ in detections} == {"framework"}


def test_client_calls_link_to_server_endpoints(make_js_ctx: MakeJsContext) -> None:
    """Two projects of one workspace: JavaScript calls resolved against TypeScript routes."""

    endpoints: list[ApiEndpointNodeModel] = [
        n
        for n, _ in detect_apis(make_js_ctx("server", project_id=1))
        if isinstance(n, ApiEndpointNodeModel)
    ]
    calls = [
        n
        for n, _ in detect_apis(make_js_ctx("client", project_id=2))
        if isinstance(n, RestCallNodeModel)
    ]

    links = {
        (call.signature, endpoint.signature, rule)
        for call in calls
        for endpoint, rule, _ in HANDLER.resolve_call(call, endpoints)
    }

    assert links == {
        ("GET /api/v1/users/{id}", "GET /api/v1/users/:id", "exact"),
        ("DELETE /api/v1/users/{id}", "DELETE /api/v1/users/:id", "exact"),
        (
            "PUT /api/v1/orders/{orderId}/status",
            "PUT /api/v1/orders/:orderId/status",
            "exact",
        ),
        ("GET /api/accounts/{id}", "GET /api/accounts/:id", "exact"),
        ("GET /api/v1/products", "GET /api/v1/products", "exact"),
        # POST /api/v1/orders: the server has no such route, nothing is linked
    }
