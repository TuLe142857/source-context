"""requests / httpx / aiohttp calls - Hướng 2, consumer side.

``base_url`` follows httpx semantics (``Client._merge_url``): a relative URL is appended to the
base path, an absolute one replaces it.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import RestApiHandler, join_url

from ..cst import ObjectInfo, Site, arg, constructor_arg, evaluate, scope_name, text

HTTP_MODULES = {
    "requests": "requests",
    "requests.api": "requests",
    "httpx": "httpx",
    "httpx._api": "httpx",
}
CLIENT_KINDS: dict[str, tuple[str, str | None]] = {
    # instance kind -> (library, keyword of the constructor holding the base URL)
    "requests.Session()": ("requests", None),
    "requests.sessions.Session()": ("requests", None),
    "httpx.Client()": ("httpx", "base_url"),
    "httpx._client.Client()": ("httpx", "base_url"),
    "httpx.AsyncClient()": ("httpx", "base_url"),
    "httpx._client.AsyncClient()": ("httpx", "base_url"),
    "aiohttp.ClientSession()": ("aiohttp", "base_url"),
    "aiohttp.client.ClientSession()": ("aiohttp", "base_url"),
}
BARE_FUNCTIONS = {"urllib.request.urlopen": "urllib"}
VERBS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})
METHOD_NAMES = VERBS | {"request", "stream", "urlopen"}

CONFIDENCE_STATIC = 0.9
CONFIDENCE_TEMPLATE = 0.8
CONFIDENCE_UNKNOWN = 0.6


def visit(
    state: dict[str, Any], ctx: ApiMapContext, path: str, site: Site, obj: ObjectInfo
) -> None:
    """Record one HTTP request made through a known library object."""

    if "handler" in site:
        return
    kind, constructor, _ = obj
    method, args = text(site["method"]), site["args"]
    library, base_keyword = _library(kind, "receiver" in site)
    if library is None:
        return

    if "receiver" not in site:  # from requests import get / urlopen(url)
        function = (kind or "").rsplit(".", 1)[-1]
        method = (
            function
            if function in VERBS or function in ("request", "stream")
            else method
        )
    http_method: str | None
    if kind in BARE_FUNCTIONS:
        http_method, url_node = "GET", arg(args, 0, "url")
    elif method in VERBS:
        http_method, url_node = method.upper(), arg(args, 0, "url")
    elif method in ("request", "stream"):
        verb = evaluate(ctx, path, arg(args, 0, "method"))
        http_method = verb.upper() if verb and "{" not in verb else None
        url_node = arg(args, 1, "url")
    else:
        return

    base, base_text = None, None
    if (
        base_keyword is not None
        and (value := constructor_arg(constructor, base_keyword)) is not None
    ):
        base, base_text = evaluate(ctx, *value), text(value[1])
    state.setdefault("calls", []).append(
        {
            "library": library,
            "method": http_method,
            "file": path,
            "site": site["site"],
            "url": join_url(base, evaluate(ctx, path, url_node)),
            "raw": text(url_node) if url_node is not None else None,
            "base_url": base_text,
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
            base_url=call["base_url"],
        )
        detections.append(
            (node, (call["file"], call["site"].start_byte, call["site"].end_byte))
        )
    return detections


def _library(kind: str | None, has_receiver: bool) -> tuple[str | None, str | None]:
    """``(library, base URL keyword)`` of the object a request is made on."""

    if kind is None:
        return None, None
    if not has_receiver:
        if kind in BARE_FUNCTIONS:
            return BARE_FUNCTIONS[kind], None
        module = kind.rsplit(".", 1)[0]
        return HTTP_MODULES.get(module), None
    if kind in HTTP_MODULES:
        return HTTP_MODULES[kind], None
    if kind in CLIENT_KINDS:
        return CLIENT_KINDS[kind]
    return None, None
