import re
from pathlib import PurePosixPath
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.base import BaseRouteExtractor
from app.route_extractor.models import ExtractedRoute
from app.route_extractor.normalizer import canonicalize_url_path
from app.route_extractor.registry import register_route_extractor


@register_route_extractor
class NextJSRouteExtractor(BaseRouteExtractor):
    language = "typescript"
    framework_name = "nextjs"

    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        p = PurePosixPath(file_path.replace("\\", "/"))
        routes: list[ExtractedRoute] = []
        text = code_bytes.decode("utf-8", errors="ignore")

        func_nodes: dict[str, FunctionNode] = {}
        if uast_root:
            self._collect_function_nodes(uast_root, func_nodes)

        # 1. Next.js App Router API Routes: app/api/.../route.ts (or js)
        if p.name in ("route.ts", "route.js", "route.mjs"):
            # Derive route path from directory
            parts = list(p.parent.parts)
            if "app" in parts:
                app_idx = parts.index("app")
                route_parts = parts[app_idx + 1 :]
                raw_path = "/" + "/".join(route_parts)
                canonical = canonicalize_url_path(raw_path)

                # Look for named exported HTTP handlers: export async function GET / POST / PUT / DELETE
                export_pattern = re.compile(
                    r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(",
                    re.MULTILINE,
                )
                for m in export_pattern.finditer(text):
                    method = m.group(1).upper()
                    fn = func_nodes.get(method)
                    routes.append(
                        ExtractedRoute(
                            method=method,
                            path=canonical,
                            raw_path=raw_path,
                            framework="nextjs_app_router",
                            handler_name=method,
                            handler_start_byte=fn.start_byte if fn else m.start(),
                            handler_end_byte=fn.end_byte if fn else m.end(),
                        )
                    )

        # 2. Next.js Pages Router API Routes: pages/api/**/*.ts (or js)
        elif "pages" in p.parts and "api" in p.parts:
            parts = list(p.parts)
            pages_idx = parts.index("pages")
            rel_parts = parts[pages_idx + 1 :]
            # Remove extension from last part
            rel_parts[-1] = p.stem
            # index.ts resolves to parent directory
            if rel_parts[-1] == "index":
                rel_parts.pop()

            raw_path = "/" + "/".join(rel_parts)
            canonical = canonicalize_url_path(raw_path)

            routes.append(
                ExtractedRoute(
                    method="ANY",
                    path=canonical,
                    raw_path=raw_path,
                    framework="nextjs_pages_router",
                    handler_name="default",
                    handler_start_byte=0,
                    handler_end_byte=len(code_bytes),
                )
            )

        return routes

    def _collect_function_nodes(self, node: UASTNode, out: dict[str, FunctionNode]) -> None:
        if isinstance(node, FunctionNode) and node.name:
            out[node.name] = node
        for child in getattr(node, "children", []):
            self._collect_function_nodes(child, out)


@register_route_extractor
class NextJSRouteExtractorJS(NextJSRouteExtractor):
    language = "javascript"
    framework_name = "nextjs"
