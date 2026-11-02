import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class FastifyRouteExtractor(BaseRouteExtractor):
    language = "typescript"
    framework_name = "fastify"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "fastify" not in text:
            return []

        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        routes: list[ExtractedRoute] = []

        # 1. fastify.get('/path', handler) or fastify.post('/path', opts, handler)
        pattern = re.compile(
            r"(?:fastify|server|app)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE,
        )
        for m in pattern.finditer(text):
            method = m.group(1).upper()
            raw_path = m.group(2)
            canonical = canonicalize_url_path(raw_path)
            routes.append(
                ExtractedRoute(
                    method=method,
                    path=canonical,
                    raw_path=raw_path,
                    framework=self.framework_name,
                    handler_name=f"fastify.{method.lower()}",
                    handler_start_byte=m.start(),
                    handler_end_byte=m.end(),
                )
            )

        # 2. fastify.route({ method: 'GET', url: '/path' })
        route_obj_pattern = re.compile(
            r"(?:fastify|server|app)\.route\s*\(\s*\{[^}]*method\s*:\s*['\"]([a-zA-Z]+)['\"][^}]*url\s*:\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE | re.DOTALL,
        )
        for m in route_obj_pattern.finditer(text):
            method = m.group(1).upper()
            raw_path = m.group(2)
            canonical = canonicalize_url_path(raw_path)
            routes.append(
                ExtractedRoute(
                    method=method,
                    path=canonical,
                    raw_path=raw_path,
                    framework=self.framework_name,
                    handler_name=f"fastify.route.{method.lower()}",
                    handler_start_byte=m.start(),
                    handler_end_byte=m.end(),
                )
            )

        return routes

    def _collect_function_nodes(self, node: UASTNode, out: dict[str, FunctionNode]) -> None:
        if isinstance(node, FunctionNode) and node.name:
            out[node.name] = node
        for child in getattr(node, "children", []):
            self._collect_function_nodes(child, out)


@register_route_extractor
class FastifyRouteExtractorJS(FastifyRouteExtractor):
    language = "javascript"
    framework_name = "fastify"
