"""Express endpoints - Hướng 2, provider side.

Routers are ``express()`` apps and ``express.Router()`` / ``Router()`` objects; ``app.use(prefix,
router)`` mounts one router under another, the same router graph as FastAPI's
``include_router``, composed by ``compose_route_paths``. Express concatenates prefixes and
paths as they are written.
"""

from __future__ import annotations

from typing import Any

from tree_sitter import Node

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Anchor, Detection
from app.engine.api_map.handlers.rest_api_handler import (
    RestApiHandler,
    compose_route_paths,
)

from ..cst import (
    FUNCTION_VALUES,
    ObjectInfo,
    Site,
    arg,
    arguments,
    binding,
    evaluate,
    resolve_object,
    scope_name,
    text,
    unwrap,
)

APP_KINDS = frozenset({"express()"})
ROUTER_KINDS = APP_KINDS | {"express.Router()"}
VERBS = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
    "head": "HEAD",
    "options": "OPTIONS",
    "all": "*",
}
METHOD_NAMES = frozenset({*VERBS, "use"})
CONFIDENCE = 0.95
UNMOUNTED_CONFIDENCE = 0.7


def visit(
    state: dict[str, Any], ctx: ApiMapContext, path: str, site: Site, obj: ObjectInfo
) -> None:
    if "receiver" not in site or "handler" in site:
        return
    method, args = text(site["method"]), site["args"]

    chain = _route_chain(ctx, path, site["receiver"]) if method in VERBS else None
    if chain is not None:  # app.route("/x").get(h).post(h)
        router_node, router_obj, path_node = chain
        router = _router(state, path, router_node, router_obj)
        _add_route(state, ctx, path, router, VERBS[method], path_node, args, site)
        return

    if obj[0] not in ROUTER_KINDS:
        return
    router = _router(state, path, site["receiver"], obj)
    if method in VERBS:
        values = arguments(args)
        if (
            len(values) >= 2
        ):  # a route needs a path and a handler; `app.get("x")` reads a setting
            _add_route(state, ctx, path, router, VERBS[method], values[0], args, site)
    elif method == "use":
        values = arguments(args)
        prefix = evaluate(ctx, path, values[0]) if values else None
        children = values[1:] if prefix is not None else values
        for child_node in children:
            child_obj = resolve_object(ctx, path, child_node)
            if child_obj[0] in ROUTER_KINDS:
                child = _router(state, path, child_node, child_obj)
                state.setdefault("mounts", []).append((router, child, prefix or ""))


def finish(
    state: dict[str, Any], handler: RestApiHandler, ctx: ApiMapContext
) -> list[Detection]:
    routers: dict[str, dict[str, Any]] = state.get("routers", {})
    prefixes = {
        key: "" for key in routers
    }  # an Express router carries no prefix of its own
    detections: list[Detection] = []
    for route in state.get("routes", []):
        for prefix, mounted in compose_route_paths(
            route["router"], prefixes, state.get("mounts", [])
        ):
            mounted = mounted or routers[route["router"]]["kind"] in APP_KINDS
            node = handler.endpoint_node(
                ctx,
                method=route["method"],
                path=prefix + route["path"],
                framework="express",
                raw=route["raw"],
                file=route["file"],
                handler_name=route["handler_name"],
                detector="framework",
                rule=f"express.{route['method'].lower() if route['method'] != '*' else 'all'}",
                confidence=CONFIDENCE if mounted else UNMOUNTED_CONFIDENCE,
                router=route["router"],
                local_path=route["path"],
                prefix=prefix,
                mounted=mounted,
            )
            detections.append((node, route["anchor"]))
    return detections


def _add_route(
    state: dict[str, Any],
    ctx: ApiMapContext,
    path: str,
    router: str,
    method: str,
    path_node: Node,
    args: Node,
    site: Site,
) -> None:
    local = evaluate(ctx, path, path_node)
    if local is None or not (local == "" or local.startswith("/") or local == "*"):
        return  # a RegExp or a computed path
    handler_name, anchor = _handler(ctx, path, arg(args, -1), site)
    state.setdefault("routes", []).append(
        {
            "router": router,
            "method": method,
            "path": local,
            "raw": text(path_node),
            "file": path,
            "handler_name": handler_name,
            "anchor": anchor,
        }
    )


def _handler(
    ctx: ApiMapContext, path: str, node: Node | None, site: Site
) -> tuple[str | None, Anchor]:
    """The last handler: a named function anchors on its definition, an inline one on the call."""

    node = unwrap(node)
    if node is not None and node.type in ("identifier", "member_expression"):
        bound = binding(ctx, path, node)
        if bound is not None and bound[0] == "definition":
            definition = bound[2]
            return scope_name(definition), (
                bound[1],
                definition.start_byte,
                definition.end_byte,
            )
    if (
        node is not None
        and node.type in FUNCTION_VALUES
        and node.child_by_field_name("name") is not None
    ):
        name = text(
            node.child_by_field_name("name")
        )  # function updateStatus(req, res) {...}
    else:
        name = None
    call = site["site"]
    return name, (path, call.start_byte, call.end_byte)


def _route_chain(
    ctx: ApiMapContext, path: str, receiver: Node
) -> tuple[Node, ObjectInfo, Node] | None:
    """``app.route("/x")`` behind ``.get(h).post(h)``: (router node, router object, path node)."""

    node = unwrap(receiver)
    while node is not None and node.type == "call_expression":
        function = node.child_by_field_name("function")
        if function is None or function.type != "member_expression":
            return None
        name = text(function.child_by_field_name("property"))
        if name == "route":
            router_node = function.child_by_field_name("object")
            router_obj = resolve_object(ctx, path, router_node)
            path_node = arg(node.child_by_field_name("arguments"), 0)
            if (
                router_node is None
                or path_node is None
                or router_obj[0] not in ROUTER_KINDS
            ):
                return None
            return router_node, router_obj, path_node
        if name not in VERBS:
            return None
        node = unwrap(function.child_by_field_name("object"))
    return None


def _router(state: dict[str, Any], path: str, node: Node, obj: ObjectInfo) -> str:
    kind, _, key = obj
    key = key or f"{path}:{node.start_byte}"
    state.setdefault("routers", {}).setdefault(key, {"kind": kind})
    return key
