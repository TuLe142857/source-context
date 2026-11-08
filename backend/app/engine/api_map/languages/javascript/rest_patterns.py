"""Hướng 1 rules for JavaScript and TypeScript: pure data, read by ``api_map/text_pattern.py``.

JS has no keyword arguments; options live in object literals (``fetch(url, { method })``,
``axios({ url, method })``), read through ``<name>_option`` entries. The same call shape
``x.get("/path", ...)`` is a route on an Express router and a request on an axios client: a
route needs a router-like receiver and a handler as last argument, and endpoint rules are
tried first.
"""

import re
from typing import Any

_STRING = (
    r"""(?P<prefix>)(?P<quote>"|'|`)(?P<body>(?:\\.|(?!(?P=quote)).)*)(?P=quote)"""
)
_VERBS = "get|post|put|patch|delete|head|options"

JAVASCRIPT_REST_PATTERNS: dict[str, Any] = {
    # ---- literal syntax ----------------------------------------------------------------
    "string": re.compile(_STRING, re.S),
    "interpolating_quotes": ("`",),  # template literals
    "hole": re.compile(r"\$\{([^{}]+)\}"),
    "identifier": re.compile(r"[A-Za-z_$][\w$.]*"),
    "concat": "+",
    "keyword": re.compile(r"(?!)"),  # no keyword arguments in JS
    "env_expression": re.compile(
        r"^(?:process\.env|import\.meta\.env)\.(?P<name>\w+)"
        r"(?:\s*(?:\|\||\?\?)\s*(?P<default>.+))?$",
        re.S,
    ),
    "handler_like": re.compile(
        r"^(?:async\s+)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|[A-Za-z_$][\w$.]*$)",
        re.S,
    ),
    # ---- evidence ----------------------------------------------------------------------
    "url_like": re.compile(r"^(?:[a-zA-Z][\w+.-]*://|\{[^}]*\}/|/)"),
    "absolute_url": re.compile(r"^[a-zA-Z][\w+.-]*://"),
    "client_receiver": re.compile(
        r"(?i)(?:^|[._])(?:axios|http|https|client|api|request|instance|service|httpclient)s?$"
    ),
    "non_http_receiver_init": re.compile(
        r"^new\s+(?:Map|WeakMap|Set|WeakSet|URLSearchParams|Headers|FormData)\b|^\{"
    ),  # `cache = new Map()` then `cache.get("/users/1")`
    "http_libraries": {
        "axios",
        "node-fetch",
        "cross-fetch",
        "got",
        "ky",
        "superagent",
        "@angular/common/http",
    },
    "http_owners": {
        "axios",
        "lib.lib.dom.d.ts",  # fetch, from scip-typescript's bundled DOM typings
    },
    "non_http_owner_prefixes": ("lib.lib.es",),  # Map#get, Array#find...
    "frameworks": {
        "express": "express",
        "@nestjs/common": "nestjs",
        "fastify": "fastify",
        "koa": "koa",
        "@koa/router": "koa",
        "hono": "hono",
    },
    # ---- endpoints ---------------------------------------------------------------------
    "endpoint_decorators": [
        {  # NestJS: @Get(":id") inside @Controller("users")
            "id": "js.decorator.nest",
            "confidence": 0.6,
            "path_arg": (0, ""),
            "relative_path": True,
            "join_segments": True,
            "class_prefix": re.compile(r"^@Controller\s*\("),
            "match": re.compile(
                r"^@(?P<verb>Get|Post|Put|Patch|Delete|Head|Options|All)\s*\("
            ),
        },
    ],
    "endpoint_calls": [
        {  # Express / Fastify / Koa router: app.get("/x", handler)
            "id": "js.call.route",
            "confidence": 0.55,
            "path_arg": (0, ""),
            "handler_arg": (-1, ""),
            "method_from_name": True,
            "requires_handler_arg": True,
            "receiver": re.compile(
                r"(?i)(?:^|[._])(?:app|server|api|\w*router|routes?)$"
            ),
            "name": re.compile(rf"{_VERBS}|all"),
        },
    ],
    # ---- calls -------------------------------------------------------------------------
    "calls": [
        {  # axios.get(url) / http.post(url, body) / this.http.get(url)
            "id": "js.call.verb",
            "confidence": 0.45,
            "url_arg": (0, ""),
            "method_from_name": True,
            "name": re.compile(_VERBS),
        },
        {  # fetch(url, { method: "PUT" })
            "id": "js.call.fetch",
            "confidence": 0.5,
            "url_arg": (0, ""),
            "method_option": (1, "method"),
            "method": "GET",
            "name_is_evidence": True,  # the global fetch only does HTTP
            "name": re.compile(r"fetch"),
        },
        {  # axios({ method, url }) / axios.request({ ... })
            "id": "js.call.config",
            "confidence": 0.45,
            "url_option": (0, "url"),
            "method_option": (0, "method"),
            "method": "GET",
            "name": re.compile(r"axios|request"),
        },
    ],
    "min_call_confidence": 0.5,
}
