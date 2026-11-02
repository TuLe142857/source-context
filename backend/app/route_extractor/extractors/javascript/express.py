import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class ExpressRouteExtractor(BaseRouteExtractor):
    language = "typescript"
    framework_name = "express"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "express" not in text and ".use(" not in text and ".get(" not in text and ".post(" not in text:
            return []

        # 1. Prefix tracking: app.use("/api/v1/webhooks", webhookRouter)
        prefix_map: dict[str, str] = {}
        for m in re.finditer(r"\.use\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*([a-zA-Z0-9_]+)\s*\)", text):
            prefix_map[m.group(2)] = m.group(1)

        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        routes: list[ExtractedRoute] = []

        # 2. Match router.get("/path", handler) or app.post("/path", (req, res) => ...)
        pattern = re.compile(
            r"([a-zA-Z0-9_]+)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*([a-zA-Z0-9_]+|\([^)]*\)\s*=>|function)",
            re.MULTILINE,
        )
        for m in pattern.finditer(text):
            receiver, method, raw_endpoint, handler_token = (
                m.group(1),
                m.group(2).upper(),
                m.group(3),
                m.group(4).strip(),
            )
            # Skip middleware mounts like router.get(authMiddleware)
            if not raw_endpoint.startswith("/") and not raw_endpoint.startswith("*"):
                continue

            prefix = prefix_map.get(receiver, "")
            full_raw_path = self._join_prefix_and_path(prefix, raw_endpoint)
            canonical = canonicalize_url_path(full_raw_path)

            handler_name = handler_token if re.match(r"^[a-zA-Z0-9_]+$", handler_token) else f"{receiver}.{method.lower()}"
            fn = func_nodes.get(handler_name)

            routes.append(
                ExtractedRoute(
                    method=method,
                    path=canonical,
                    raw_path=full_raw_path,
                    framework=self.framework_name,
                    handler_name=handler_name,
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


# Register for JavaScript as well
@register_route_extractor
class ExpressRouteExtractorJS(ExpressRouteExtractor):
    language = "javascript"
    framework_name = "express"
