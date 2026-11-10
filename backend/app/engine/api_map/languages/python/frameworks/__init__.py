"""Framework and library specs of the Python REST detector (Hướng 2).

Each spec is ``(METHOD_NAMES, visit, finish)``: the called names it looks at, a per-site callback
filling its own ``state`` dict, and a project-level step turning that state into detections.
Adding a framework is adding a module and a line here.
"""

from collections.abc import Callable
from typing import Any

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import RestApiHandler

from ..cst import ObjectInfo, Site
from . import fastapi, http_clients

type Visit = Callable[[dict[str, Any], ApiMapContext, str, Site, ObjectInfo], None]
type Finish = Callable[[dict[str, Any], RestApiHandler, ApiMapContext], list[Detection]]

PYTHON_REST_FRAMEWORKS: dict[str, tuple[frozenset[str], Visit, Finish]] = {
    "fastapi": (fastapi.METHOD_NAMES, fastapi.visit, fastapi.finish),
    "http_clients": (
        http_clients.METHOD_NAMES,
        http_clients.visit,
        http_clients.finish,
    ),
}
