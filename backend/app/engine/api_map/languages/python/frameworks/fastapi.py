"""FastAPI endpoints - Hướng 2, provider side.

Routes are recorded per router while the files are read; full paths are composed in ``finish``,
once every file is read, because ``include_router`` usually lives in another file than the
routes. Path formula, as in FastAPI itself::

    full = Σ over the include chain (parent prefix + include prefix) + router prefix + route path
"""

from __future__ import annotations

from typing import Any

from tree_sitter import Node

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import (
    RestApiHandler,
    compose_route_paths,
)

from ..cst import (
    ObjectInfo,
    Site,
    arg,
    binding,
    constructor_arg,
    evaluate,
    resolve_object,
    scope_name,
    text,
)

APP_KINDS = frozenset(
    {
        "fastapi.FastAPI()",
        "fastapi.applications.FastAPI()",
        "starlette.applications.Starlette()",
    }
)
ROUTER_KINDS = APP_KINDS | {"fastapi.APIRouter()", "fastapi.routing.APIRouter()"}
VERB_DECORATORS = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
    "head": "HEAD",
    "options": "OPTIONS",
    "trace": "TRACE",
}
METHOD_NAMES = frozenset(
    {*VERB_DECORATORS, "api_route", "add_api_route", "include_router", "mount"}
)
CONFIDENCE = 0.95
UNMOUNTED_CONFIDENCE = 0.7
"""A router no ``include_router`` reaches (or whose include was not found): its paths may lack a prefix."""


def visit(
    state: dict[str, Any], ctx: ApiMapContext, path: str, site: Site, obj: ObjectInfo
) -> None:
    """Record routers, routes and mounts of one site."""

    if obj[0] not in ROUTER_KINDS or "receiver" not in site:
        return
    router = _router(state, ctx, path, site["receiver"], obj)
    method, args = text(site["method"]), site["args"]
    routes: list[dict[str, Any]] = state.setdefault("routes", [])

    if "handler" in site:  # @router.get("/x") / @router.api_route("/x", methods=[...])
        methods = _methods(ctx, path, method, args)
        if methods:
            routes.append(
                {
                    "router": router,
                    "methods": methods,
                    "file": path,
                    "rule": f"fastapi.{method}",
                    "path": arg(args, 0, "path"),
                    "handler": (path, site["handler"]),
                }
            )
    elif (
        method == "add_api_route"
    ):  # router.add_api_route("/x", endpoint, methods=[...])
        endpoint = arg(args, 1, "endpoint")
        bound = (
            binding(ctx, path, endpoint)
            if endpoint is not None and endpoint.type == "identifier"
            else None
        )
        routes.append(
            {
                "router": router,
                "methods": _methods(ctx, path, "api_route", args),
                "file": path,
                "rule": "fastapi.add_api_route",
                "path": arg(args, 0, "path"),
                "handler": (bound[1], bound[2])
                if bound is not None and bound[0] == "definition"
                else None,
            }
        )
    elif method in (
        "include_router",
        "mount",
    ):  # parent.include_router(child, prefix=...)
        child_node = (
            arg(args, 0, "router")
            if method == "include_router"
            else arg(args, 1, "app")
        )
        child_obj = resolve_object(ctx, path, child_node)
        if child_node is not None and child_obj[0] in ROUTER_KINDS:
            child = _router(state, ctx, path, child_node, child_obj)
            prefix_node = (
                arg(args, None, "prefix")
                if method == "include_router"
                else arg(args, 0, "path")
            )
            state.setdefault("mounts", []).append(
                (router, child, evaluate(ctx, path, prefix_node) or "")
            )


def finish(
    state: dict[str, Any], handler: RestApiHandler, ctx: ApiMapContext
) -> list[Detection]:
    """One endpoint per route, method and include chain."""

    routers: dict[str, dict[str, Any]] = state.get("routers", {})
    prefixes = {key: info["prefix"] for key, info in routers.items()}
    mounts = state.get("mounts", [])
    detections: list[Detection] = []
    for route in state.get("routes", []):
        path_node: Node | None = route["path"]
        value = evaluate(ctx, route["file"], path_node) if path_node is not None else ""
        local = (
            value if value is not None else "{}"
        )  # "" is a valid route path: `@router.post("")`
        handler_name, anchor = None, None
        if route["handler"] is not None:
            handler_path, function = route["handler"]
            handler_name = scope_name(function)
            anchor = (handler_path, function.start_byte, function.end_byte)
        for prefix, mounted in compose_route_paths(route["router"], prefixes, mounts):
            mounted = mounted or routers[route["router"]]["kind"] in APP_KINDS
            for method in route["methods"]:
                node = handler.endpoint_node(
                    ctx,
                    method=method,
                    path=prefix + local,
                    framework="fastapi",
                    raw=text(path_node) if path_node is not None else None,
                    file=route["file"],
                    handler_name=handler_name,
                    detector="framework",
                    rule=route["rule"],
                    confidence=CONFIDENCE if mounted else UNMOUNTED_CONFIDENCE,
                    router=route["router"],
                    local_path=local,
                    prefix=prefix,
                    mounted=mounted,
                )
                detections.append((node, anchor))
    return detections


def _router(
    state: dict[str, Any], ctx: ApiMapContext, path: str, node: Node, obj: ObjectInfo
) -> str:
    """Register a router once, keyed by its SCIP symbol (``file:offset`` without one)."""

    kind, constructor, key = obj
    key = key or f"{path}:{node.start_byte}"
    routers: dict[str, dict[str, Any]] = state.setdefault("routers", {})
    if key not in routers:
        prefix = ""
        if (
            kind not in APP_KINDS
            and (value := constructor_arg(constructor, "prefix")) is not None
        ):
            prefix = evaluate(ctx, *value) or ""
        routers[key] = {"kind": kind, "prefix": prefix}
    return key


def _methods(ctx: ApiMapContext, path: str, method: str, args: Node) -> list[str]:
    if method in VERB_DECORATORS:
        return [VERB_DECORATORS[method]]
    if method != "api_route":
        return []
    listed = arg(args, None, "methods")
    if listed is None:
        return ["GET"]  # FastAPI default
    values = [evaluate(ctx, path, item) for item in listed.named_children]
    return [value.upper() for value in values if value and "{" not in value] or ["*"]
