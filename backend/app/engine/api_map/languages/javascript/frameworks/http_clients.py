"""axios / fetch / Angular HttpClient calls - Hướng 2, consumer side.

``axios.create({ baseURL })`` instances join their base like httpx clients do; ``fetch`` and
``axios(config)`` read the method and URL from their options object.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from tree_sitter import Node

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import RestApiHandler, join_url

from ..cst import (
    ObjectInfo,
    Site,
    arg,
    binding,
    constructor_property,
    evaluate,
    object_property,
    scope_name,
    text,
)

VERBS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})
WITH_BODY = frozenset({"post", "put", "patch"})
MODULES = {"axios": "axios", "node-fetch": "fetch", "cross-fetch": "fetch"}
CLIENT_KINDS: dict[str, tuple[str, int | None, str | None]] = {
    # instance kind -> (library, constructor argument holding the options, base URL property)
    "axios.create()": ("axios", 0, "baseURL"),
    "axios.default.create()": ("axios", 0, "baseURL"),
    "@angular/common/http.HttpClient()": ("angular", None, None),
}
GLOBAL_FETCH_OWNERS = frozenset({"window", "globalThis", "self"})
METHOD_NAMES = VERBS | {"request", "fetch", "axios"}

CONFIDENCE_STATIC = 0.9
CONFIDENCE_TEMPLATE = 0.8
CONFIDENCE_UNKNOWN = 0.6


def visit(
    state: dict[str, Any], ctx: ApiMapContext, path: str, site: Site, obj: ObjectInfo
) -> None:
    if "handler" in site:
        return
    kind, constructor, _ = obj
    method, args = text(site["method"]), site["args"]
    found: tuple[str, str | None, Node | None, str | None] | None = (
        None  # (library, method, url, base)
    )

    if "receiver" not in site:
        if method == "fetch" and (
            kind in ("node-fetch", "cross-fetch") or _global(ctx, path, site["method"])
        ):
            found = (
                "fetch",
                _option_method(ctx, path, arg(args, 1)) or "GET",
                arg(args, 0),
                None,
            )
        elif kind == "axios":  # axios(config) / axios(url, config)
            found = _config_call(ctx, path, args, "axios", None)
    elif method == "fetch" and text(site["receiver"]) in GLOBAL_FETCH_OWNERS:
        found = (
            "fetch",
            _option_method(ctx, path, arg(args, 1)) or "GET",
            arg(args, 0),
            None,
        )
    else:
        library, base = _client(ctx, kind, constructor)
        if library is not None:
            if method in VERBS:
                found = (library, method.upper(), arg(args, 0), base)
            elif method == "request" and library == "axios":
                found = _config_call(ctx, path, args, library, base)
            elif method == "request":  # HttpClient.request("GET", url)
                verb = evaluate(ctx, path, arg(args, 0))
                found = (
                    library,
                    verb.upper() if verb and "{" not in verb else None,
                    arg(args, 1),
                    base,
                )

    if found is None:
        return
    library, http_method, url_node, base = found
    state.setdefault("calls", []).append(
        {
            "library": library,
            "method": http_method,
            "file": path,
            "site": site["site"],
            "url": join_url(base, evaluate(ctx, path, url_node)),
            "raw": text(url_node) if url_node is not None else None,
        }
    )


def finish(
    state: dict[str, Any], handler: RestApiHandler, ctx: ApiMapContext
) -> list[Detection]:
    ordinals: Counter[tuple[str, str, str | None, str | None]] = Counter()
    detections: list[Detection] = []
    for call in state.get("calls", []):
        scope = scope_name(call["site"])
        identity = (call["file"], scope, call["method"], call["raw"])
        ordinals[identity] += 1
        url = call["url"]
        if url is None:
            confidence = CONFIDENCE_UNKNOWN
        else:
            confidence = CONFIDENCE_TEMPLATE if "{" in url else CONFIDENCE_STATIC
        node = handler.call_node(
            ctx,
            method=call["method"],
            url=url,
            library=call["library"],
            raw=call["raw"],
            file=call["file"],
            scope=scope,
            ordinal=ordinals[identity],
            detector="framework",
            rule=f"{call['library']}.call",
            confidence=confidence,
        )
        detections.append(
            (node, (call["file"], call["site"].start_byte, call["site"].end_byte))
        )
    return detections


def _client(
    ctx: ApiMapContext, kind: str | None, constructor: Any
) -> tuple[str | None, str | None]:
    """(library, base URL) of the object a request is made on."""

    if kind is None:
        return None, None
    if kind in MODULES and MODULES[kind] == "axios":
        return "axios", None
    if kind in CLIENT_KINDS:
        library, position, prop = CLIENT_KINDS[kind]
        base = None
        if position is not None and prop is not None:
            value = constructor_property(constructor, position, prop)
            base = evaluate(ctx, *value) if value is not None else None
        return library, base
    return None, None


def _config_call(
    ctx: ApiMapContext, path: str, args: Node, library: str, base: str | None
) -> tuple[str, str | None, Node | None, str | None]:
    """``axios({ method, url })`` / ``axios(url, { method })``; axios defaults to GET."""

    first = arg(args, 0)
    if first is not None and first.type == "object":
        return (
            library,
            _option_method(ctx, path, first) or "GET",
            object_property(first, "url"),
            base,
        )
    return library, _option_method(ctx, path, arg(args, 1)) or "GET", first, base


def _option_method(ctx: ApiMapContext, path: str, options: Node | None) -> str | None:
    value = evaluate(ctx, path, object_property(options, "method"))
    return value.upper() if value and "{" not in value else None


def _global(ctx: ApiMapContext, path: str, name: Node) -> bool:
    """``fetch`` is the global one unless the project binds that name itself."""

    return binding(ctx, path, name) is None
