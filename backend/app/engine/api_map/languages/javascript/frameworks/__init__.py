"""Framework and library specs of the JavaScript / TypeScript REST detector (Hướng 2).

Same contract as ``languages/python/frameworks``: ``(METHOD_NAMES, visit, finish)``.
"""

from collections.abc import Callable
from typing import Any

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import RestApiHandler

from ..cst import ObjectInfo, Site
from . import express, http_clients, nestjs

type Visit = Callable[[dict[str, Any], ApiMapContext, str, Site, ObjectInfo], None]
type Finish = Callable[[dict[str, Any], RestApiHandler, ApiMapContext], list[Detection]]

JAVASCRIPT_REST_FRAMEWORKS: dict[str, tuple[frozenset[str], Visit, Finish]] = {
    "express": (express.METHOD_NAMES, express.visit, express.finish),
    "nestjs": (nestjs.METHOD_NAMES, nestjs.visit, nestjs.finish),
    "http_clients": (
        http_clients.METHOD_NAMES,
        http_clients.visit,
        http_clients.finish,
    ),
}
