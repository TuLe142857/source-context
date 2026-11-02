import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class FastAPIRouteExtractor(BaseRouteExtractor):
    language = "python"
    framework_name = "fastapi"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "fastapi" not in text and "@app." not in text and "@router." not in text and "APIRouter" not in text:
            return []

        # 1. Scan for APIRouter prefix: router = APIRouter(prefix="/api/v1/inventory")
        prefix_map: dict[str, str] = {}
        for match in re.finditer(
            r"(\w+)\s*=\s*APIRouter\s*\([^)]*prefix\s*=\s*['\"]([^'\"]+)['\"]",
            text,
        ):
            var_name, prefix = match.group(1), match.group(2)
            prefix_map[var_name] = prefix

        # Map function definitions if UAST is available
        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        routes: list[ExtractedRoute] = []

        # 2. Match standard route decorators: @app.get("/path"), @router.post("/path")
        decorator_pattern = re.compile(
            r"@(\w+)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"]([^'\"]+)['\"]"
            r"(?:[^)]*\))?\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)",
            re.MULTILINE,
        )
        for m in decorator_pattern.finditer(text):
            receiver, method, raw_endpoint, func_name = (
                m.group(1),
                m.group(2).upper(),
                m.group(3),
                m.group(4),
            )
            prefix = prefix_map.get(receiver, "")
            full_raw_path = self._join_prefix_and_path(prefix, raw_endpoint)
            canonical = canonicalize_url_path(full_raw_path)

            fn = func_nodes.get(func_name)
            routes.append(
                ExtractedRoute(
                    method=method,
                    path=canonical,
                    raw_path=full_raw_path,
                    framework=self.framework_name,
                    handler_name=func_name,
                    handler_start_byte=fn.start_byte if fn else m.start(),
                    handler_end_byte=fn.end_byte if fn else m.end(),
                    metadata={"receiver": receiver, "prefix": prefix},
                )
            )

        # 3. Match @app.api_route("/path", methods=["GET", "POST"])
        api_route_pattern = re.compile(
            r"@(\w+)\.api_route\s*\(\s*['\"]([^'\"]+)['\"][^)]*methods\s*=\s*\[([^\]]+)\]"
            r"(?:[^)]*\))?\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)",
            re.MULTILINE,
        )
        for m in api_route_pattern.finditer(text):
            receiver, raw_endpoint, methods_str, func_name = (
                m.group(1),
                m.group(2),
                m.group(3),
                m.group(4),
            )
            methods = re.findall(r"['\"]([a-zA-Z]+)['\"]", methods_str) or ["GET"]
            prefix = prefix_map.get(receiver, "")
            full_raw_path = self._join_prefix_and_path(prefix, raw_endpoint)
            canonical = canonicalize_url_path(full_raw_path)
            fn = func_nodes.get(func_name)

            for method in methods:
                routes.append(
                    ExtractedRoute(
                        method=method.upper(),
                        path=canonical,
                        raw_path=full_raw_path,
                        framework=self.framework_name,
                        handler_name=func_name,
                        handler_start_byte=fn.start_byte if fn else m.start(),
                        handler_end_byte=fn.end_byte if fn else m.end(),
                        metadata={"receiver": receiver, "prefix": prefix},
                    )
                )

        return routes

    def _join_prefix_and_path(self, prefix: str, path: str) -> str:
        if not prefix:
            return path
        return prefix.rstrip("/") + "/" + path.lstrip("/")

    def _collect_function_nodes(self, node: UASTNode, out: dict[str, FunctionNode]) -> None:
        if isinstance(node, FunctionNode) and node.name:
            out[node.name] = node
        for child in getattr(node, "children", []):
            self._collect_function_nodes(child, out)
