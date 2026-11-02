import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class LitestarSanicRouteExtractor(BaseRouteExtractor):
    language = "python"
    framework_name = "litestar_sanic"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        text = code_bytes.decode("utf-8", errors="ignore")
        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        routes: list[ExtractedRoute] = []

        # 1. Litestar handlers: @get("/path"), @post("/path")
        litestar_pattern = re.compile(
            r"@(get|post|put|delete|patch)\s*\(\s*(?:path\s*=\s*)?['\"]([^'\"]+)['\"]"
            r"(?:[^)]*\))?\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)",
            re.MULTILINE,
        )
        for m in litestar_pattern.finditer(text):
            method, raw_endpoint, func_name = m.group(1).upper(), m.group(2), m.group(3)
            canonical = canonicalize_url_path(raw_endpoint)
            fn = func_nodes.get(func_name)
            routes.append(
                ExtractedRoute(
                    method=method,
                    path=canonical,
                    raw_path=raw_endpoint,
                    framework="litestar",
                    handler_name=func_name,
                    handler_start_byte=fn.start_byte if fn else m.start(),
                    handler_end_byte=fn.end_byte if fn else m.end(),
                )
            )

        return routes

    def _collect_function_nodes(self, node: UASTNode, out: dict[str, FunctionNode]) -> None:
        if isinstance(node, FunctionNode) and node.name:
            out[node.name] = node
        for child in getattr(node, "children", []):
            self._collect_function_nodes(child, out)
