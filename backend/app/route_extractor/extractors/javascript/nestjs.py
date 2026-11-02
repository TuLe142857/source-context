import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class NestJSRouteExtractor(BaseRouteExtractor):
    language = "typescript"
    framework_name = "nestjs"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "@Controller" not in text:
            return []

        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        routes: list[ExtractedRoute] = []

        # 1. Extract controller prefix: @Controller('users') or @Controller('/api/v1/users')
        ctrl_match = re.search(r"@Controller\s*\(\s*(?:['\"]([^'\"]*)['\"])?\s*\)", text)
        ctrl_prefix = ctrl_match.group(1) if (ctrl_match and ctrl_match.group(1)) else ""
        if ctrl_prefix and not ctrl_prefix.startswith("/"):
            ctrl_prefix = "/" + ctrl_prefix

        # 2. Extract method decorators: @Get(':id'), @Post(), @Delete(':id')
        method_pattern = re.compile(
            r"@(Get|Post|Put|Delete|Patch|Options|Head)\s*\(\s*(?:['\"]([^'\"]*)['\"])?\s*\)"
            r"(?:[^{;]*?)(?:async\s+)?([a-zA-Z0-9_]+)\s*\(",
            re.MULTILINE | re.DOTALL,
        )
        for m in method_pattern.finditer(text):
            method = m.group(1).upper()
            sub_path = m.group(2) or ""
            handler_name = m.group(3)

            full_path = self._join_prefix_and_path(ctrl_prefix, sub_path)
            canonical = canonicalize_url_path(full_path)
            fn = func_nodes.get(handler_name)

            routes.append(
                ExtractedRoute(
                    method=method,
                    path=canonical,
                    raw_path=full_path,
                    framework=self.framework_name,
                    handler_name=handler_name,
                    handler_start_byte=fn.start_byte if fn else m.start(),
                    handler_end_byte=fn.end_byte if fn else m.end(),
                    metadata={"controller_prefix": ctrl_prefix},
                )
            )

        return routes

    def _join_prefix_and_path(self, prefix: str, path: str) -> str:
        prefix = prefix.strip("/")
        path = path.strip("/")
        if prefix and path:
            return f"/{prefix}/{path}"
        if prefix:
            return f"/{prefix}"
        if path:
            return f"/{path}"
        return "/"

    def _collect_function_nodes(self, node: UASTNode, out: dict[str, FunctionNode]) -> None:
        if isinstance(node, FunctionNode) and node.name:
            out[node.name] = node
        for child in getattr(node, "children", []):
            self._collect_function_nodes(child, out)
