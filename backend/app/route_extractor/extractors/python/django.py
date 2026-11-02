import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class DjangoRouteExtractor(BaseRouteExtractor):
    language = "python"
    framework_name = "django"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "urlpatterns" not in text and "path(" not in text and "re_path(" not in text:
            return []

        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        routes: list[ExtractedRoute] = []

        # Matches: path('api/v1/orders/', views.order_list) or re_path(r'^api/v1/orders/', ...)
        pattern = re.compile(
            r"(?:path|re_path)\s*\(\s*(?:r?['\"])([^'\"]+)(?:['\"])\s*,\s*([a-zA-Z0-9_.]+)",
            re.MULTILINE,
        )
        for m in pattern.finditer(text):
            raw_path = m.group(1).lstrip("^").rstrip("$")
            if not raw_path.startswith("/"):
                raw_path = "/" + raw_path
            canonical = canonicalize_url_path(raw_path)
            view_ref = m.group(2)
            handler_name = view_ref.split(".")[-1]

            fn = func_nodes.get(handler_name)
            routes.append(
                ExtractedRoute(
                    method="ANY",
                    path=canonical,
                    raw_path=raw_path,
                    framework=self.framework_name,
                    handler_name=handler_name,
                    handler_start_byte=fn.start_byte if fn else m.start(),
                    handler_end_byte=fn.end_byte if fn else m.end(),
                    metadata={"view_ref": view_ref},
                )
            )

        return routes

    def _collect_function_nodes(self, node: UASTNode, out: dict[str, FunctionNode]) -> None:
        if isinstance(node, FunctionNode) and node.name:
            out[node.name] = node
        for child in getattr(node, "children", []):
            self._collect_function_nodes(child, out)
