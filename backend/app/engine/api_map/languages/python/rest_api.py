"""REST detection for Python: both approaches, merged later by ``build.merge_detections``."""

import logging
from typing import Any

from app.engine.api_map import text_pattern
from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import RestApiHandler

from .cst import iter_sites, site_object, text
from .frameworks import PYTHON_REST_FRAMEWORKS
from .rest_patterns import PYTHON_REST_PATTERNS

logger = logging.getLogger(__name__)


class PythonRestApiHandler(RestApiHandler):
    def __init__(self) -> None:
        super().__init__(kind="rest", language="python")

    def detect_api(self, ctx: ApiMapContext) -> list[Detection]:
        paths = ctx.paths(self.language)
        detections = self._detect_frameworks(ctx, paths)  # Hướng 2
        detections += text_pattern.detect(
            self, ctx, paths, PYTHON_REST_PATTERNS
        )  # Hướng 1
        return detections

    def _detect_frameworks(
        self, ctx: ApiMapContext, paths: list[str]
    ) -> list[Detection]:
        """One pass over the call sites of every file, dispatched to the interested specs."""

        states: dict[str, dict[str, Any]] = {
            name: {} for name in PYTHON_REST_FRAMEWORKS
        }
        method_names = frozenset().union(
            *(names for names, _, _ in PYTHON_REST_FRAMEWORKS.values())
        )
        for path in paths:
            try:
                sites = list(iter_sites(ctx, path, method_names))
            except OSError:
                logger.warning("Cannot read %s, skipping", path)
                continue
            for site in sites:
                obj = site_object(ctx, path, site)
                method = text(site["method"])
                for name, (names, visit, _) in PYTHON_REST_FRAMEWORKS.items():
                    if method in names:
                        visit(states[name], ctx, path, site, obj)

        detections: list[Detection] = []
        for name, (_, _, finish) in PYTHON_REST_FRAMEWORKS.items():
            detections += finish(states[name], self, ctx)
        return detections
