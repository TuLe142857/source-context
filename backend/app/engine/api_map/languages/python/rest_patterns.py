"""Hướng 1 rules for Python: pure data, read by ``app/engine/api_map/text_pattern.py``.

Adding a framework or a client library to the pattern detector is adding a row here.
"""

import re
from typing import Any

_STRING = r"""(?P<prefix>[rRbBuUfF]{0,2})(?P<quote>\"\"\"|'''|"|')(?P<body>(?:\\.|(?!(?P=quote)).)*)(?P=quote)"""
_VERBS = "get|post|put|patch|delete|head|options"

PYTHON_REST_PATTERNS: dict[str, Any] = {
    # ---- literal syntax ----------------------------------------------------------------
    "string": re.compile(_STRING, re.S),
    "interpolating_prefix": "f",  # prefixes whose {expr} are holes
    "hole": re.compile(r"\{([^{}!:]+)[^{}]*\}"),  # {expr!r:fmt} -> expr
    "identifier": re.compile(r"[A-Za-z_][\w.]*"),
    "concat": "+",
    "keyword": re.compile(r"^([A-Za-z_]\w*)\s*=(?!=)\s*(.*)$", re.S),
    "env_getter": re.compile(r"^(?:os\.)?(?:getenv|environ\.get)\s*\("),
    "router_constructor": re.compile(r"^(?:[\w.]*\.)?\w*(?:Router|Blueprint)\s*\("),
    "router_prefix_keywords": ("prefix", "url_prefix"),
    # ---- evidence ----------------------------------------------------------------------
    "url_like": re.compile(r"^(?:[a-zA-Z][\w+.-]*://|\{[^}]*\}/|/)"),
    "absolute_url": re.compile(r"^[a-zA-Z][\w+.-]*://"),
    "client_receiver": re.compile(
        r"(?i)(?:^|[._])(?:requests|httpx|aiohttp|session|client|http|api)s?$"
    ),
    "non_http_receiver_init": re.compile(
        r"^(?:\{|dict\(|defaultdict\(|OrderedDict\(|set\()"
    ),  # `cache = {}` then `cache.get("/users/1")`
    "http_libraries": {"requests", "httpx", "aiohttp", "urllib", "urllib3"},
    "http_owners": {
        "requests",
        "requests.api",
        "requests.sessions.Session()",
        "httpx",
        "httpx._api",
        "httpx._client.Client()",
        "httpx._client.AsyncClient()",
        "aiohttp.client.ClientSession()",
        "urllib.request",
    },
    "non_http_owner_prefixes": (
        "builtins.",
        "typing.",
        "collections.",
        "os.",
        "json.",
        "configparser.",
    ),
    "frameworks": {
        "fastapi": "fastapi",
        "flask": "flask",
        "starlette": "starlette",
        "django": "django",
        "sanic": "sanic",
        "litestar": "litestar",
    },
    # ---- endpoints ---------------------------------------------------------------------
    "endpoint_decorators": [
        {
            "id": "py.decorator.verb",
            "confidence": 0.6,
            "path_arg": (0, "path"),
            "match": re.compile(
                rf"^@(?P<receiver>[\w.]+)\.(?P<verb>{_VERBS}|trace)\s*\("
            ),
        },
        {
            "id": "py.decorator.route",
            "confidence": 0.5,
            "path_arg": (0, "path"),
            "methods_kw": "methods",
            "default_methods": ("GET",),
            "match": re.compile(r"^@(?P<receiver>[\w.]+)\.(?:route|api_route)\s*\("),
        },
    ],
    "endpoint_calls": [
        {
            "id": "py.call.add_route",
            "confidence": 0.5,
            "path_arg": (0, "path"),
            "handler_arg": (1, "endpoint"),
            "methods_kw": "methods",
            "default_methods": ("GET",),
            "name": re.compile(r"add_api_route|add_url_rule|add_route"),
        },
        {
            "id": "py.call.django_path",
            "confidence": 0.4,
            "path_arg": (0, "route"),
            "handler_arg": (1, "view"),
            "default_methods": ("*",),
            "relative_path": True,
            "requires_import": "django",
            "name": re.compile(r"path|re_path"),
        },
    ],
    # ---- calls -------------------------------------------------------------------------
    "calls": [
        {
            "id": "py.call.verb",
            "confidence": 0.45,
            "url_arg": (0, "url"),
            "method_from_name": True,
            "name": re.compile(_VERBS),
        },
        {
            "id": "py.call.request",
            "confidence": 0.4,
            "method_arg": (0, "method"),
            "url_arg": (1, "url"),
            "name": re.compile(r"request|stream"),
        },
        {
            "id": "py.call.urlopen",
            "confidence": 0.4,
            "url_arg": (0, "url"),
            "method": "GET",
            "name": re.compile(r"urlopen"),
        },
    ],
    "min_call_confidence": 0.5,
}
