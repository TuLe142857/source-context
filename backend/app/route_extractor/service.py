import logging
from typing import Sequence
from neomodel import db

from app.parser.uast import UASTNode, FunctionNode
from .models import ExtractedRoute
from .registry import get_route_extractor_registry
import app.route_extractor.extractors  # Ensures all extractors are registered

logger = logging.getLogger(__name__)


class RouteIndexingService:
    """Service orchestrating extraction and Neo4j graph persistence of HTTP routes."""

    def __init__(self) -> None:
        self.registry = get_route_extractor_registry()

    def resolve_language(self, file_path: str) -> str | None:
        p = file_path.lower()
        if p.endswith(".py"):
            return "python"
        if p.endswith((".ts", ".tsx")):
            return "typescript"
        if p.endswith((".js", ".jsx", ".mjs", ".cjs")):
            return "javascript"
        return None

    def extract_routes_from_file(
        self,
        file_path: str,
        file_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> list[ExtractedRoute]:
        lang = self.resolve_language(file_path)
        if not lang:
            return []

        extractors = self.registry.get_extractors_for_language(lang)
        all_routes: list[ExtractedRoute] = []

        for ext in extractors:
            try:
                routes = ext.extract_routes(file_path, file_bytes, uast_root)
                all_routes.extend(routes)
            except Exception as e:
                logger.warning(
                    "Extractor %s failed on file %s: %s",
                    ext.framework_name,
                    file_path,
                    e,
                )

        return all_routes

    def extract_and_persist_file_routes(
        self,
        project_id: int,
        file_path: str,
        file_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> int:
        """Extracts routes for a file and persists them into Neo4j."""
        routes = self.extract_routes_from_file(file_path, file_bytes, uast_root)
        if not routes:
            return 0

        # Collect function UIDs from UAST to link with HANDLES edges
        func_map: dict[str, str] = {}
        if uast_root:
            self._collect_function_uids(uast_root, func_map)

        persisted_count = 0
        for route in routes:
            try:
                route_uid = f"route__{project_id}__{route.method}__{route.path}"
                func_uid = func_map.get(route.handler_name) if route.handler_name else None

                # 1. Merge Route node and link (Project)-[:EXPOSES]->(Route)
                cypher_base = """
                MERGE (r:Route {uid: $route_uid})
                ON CREATE SET r.method = $method,
                              r.path = $path,
                              r.raw_path = $raw_path,
                              r.protocol = $protocol,
                              r.framework = $framework
                ON MATCH SET r.raw_path = $raw_path,
                             r.framework = $framework
                WITH r
                MATCH (p:Project {uid: $project_id})
                MERGE (p)-[:EXPOSES]->(r)
                RETURN r.uid
                """
                params = {
                    "route_uid": route_uid,
                    "method": route.method,
                    "path": route.path,
                    "raw_path": route.raw_path,
                    "protocol": route.protocol,
                    "framework": route.framework,
                    "project_id": project_id,
                }
                db.cypher_query(cypher_base, params)

                # 2. If handler Function was identified, link (Function)-[:HANDLES]->(Route)
                if func_uid:
                    cypher_handler = """
                    MATCH (r:Route {uid: $route_uid})
                    MATCH (fn:Function {uid: $func_uid})
                    MERGE (fn)-[:HANDLES]->(r)
                    """
                    db.cypher_query(cypher_handler, {"route_uid": route_uid, "func_uid": func_uid})

                persisted_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to persist route %s %s in project %d: %s",
                    route.method,
                    route.path,
                    project_id,
                    e,
                )

        logger.info(
            "Persisted %d routes for file %s in project %d",
            persisted_count,
            file_path,
            project_id,
        )
        return persisted_count

    def _collect_function_uids(self, node: UASTNode, out: dict[str, str]) -> None:
        if isinstance(node, FunctionNode) and node.name and node.id:
            out[node.name] = node.id
        for child in getattr(node, "children", []):
            self._collect_function_uids(child, out)


_SERVICE = RouteIndexingService()


def get_route_indexing_service() -> RouteIndexingService:
    return _SERVICE
