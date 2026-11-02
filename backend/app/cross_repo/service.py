import hashlib
import logging
from pathlib import Path
from typing import Any, Sequence
from neomodel import db

from app.parser.uast import UASTNode, FunctionNode
from .ir import ClientCallSite, CrossRepoMatchResult, WorkspaceCrossRepoSummary
from .call_extractor import UniversalClientCallExtractor
from .matcher import is_segment_match, is_method_match, determine_rule_level

logger = logging.getLogger(__name__)


class CrossRepoService:
    """Service managing client call-site extraction, graph persistence, and cross-repo route matching."""

    def __init__(self) -> None:
        self.call_extractor = UniversalClientCallExtractor()

    def extract_and_persist_file_calls(
        self,
        project_id: int,
        file_path: str,
        file_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> int:
        """Extract outgoing HTTP calls from a file and persist them as HttpCallSite nodes in Neo4j."""
        calls = self.call_extractor.extract_calls(
            file_path=file_path,
            code_bytes=file_bytes,
            project_id=project_id,
            uast_root=uast_root,
        )
        if not calls:
            return 0

        persisted_count = 0
        for call in calls:
            try:
                # Generate a deterministic unique ID for the call site
                raw_hash = hashlib.sha256(
                    f"{project_id}:{file_path}:{call.method}:{call.canonical_path}:{call.metadata.get('offset', 0)}".encode()
                ).hexdigest()[:16]
                call_uid = f"call__{project_id}__{raw_hash}"

                cypher = """
                MERGE (c:HttpCallSite {uid: $call_uid})
                ON CREATE SET c.method = $method,
                              c.raw_path = $raw_path,
                              c.canonical_path = $canonical_path,
                              c.client_library = $client_library,
                              c.file_path = $file_path,
                              c.caller_name = $caller_name
                ON MATCH SET c.raw_path = $raw_path,
                             c.canonical_path = $canonical_path,
                             c.client_library = $client_library,
                             c.file_path = $file_path,
                             c.caller_name = $caller_name
                WITH c
                MATCH (p:Project {uid: $project_id})
                MERGE (p)-[:CONTAINS_CALL]->(c)
                RETURN c.uid
                """
                params = {
                    "call_uid": call_uid,
                    "method": call.method,
                    "raw_path": call.raw_path,
                    "canonical_path": call.canonical_path,
                    "client_library": call.client_library,
                    "file_path": call.file_path,
                    "caller_name": call.caller_func_name,
                    "project_id": project_id,
                }
                db.cypher_query(cypher, params)

                # Link enclosing Function -> HttpCallSite if caller_func_uid is known
                if call.caller_func_uid:
                    link_cypher = """
                    MATCH (c:HttpCallSite {uid: $call_uid})
                    MATCH (fn:Function {uid: $func_uid})
                    MERGE (fn)-[:MAKES_HTTP_CALL]->(c)
                    """
                    db.cypher_query(link_cypher, {"call_uid": call_uid, "func_uid": call.caller_func_uid})

                persisted_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to persist call site %s %s in project %d: %s",
                    call.method,
                    call.raw_path,
                    project_id,
                    e,
                )

        logger.info(
            "[CallSite Extractor] Persisted %d outgoing HTTP call(s) for file '%s' (Project ID: %d): %s",
            persisted_count,
            file_path,
            project_id,
            [f"{c.method} {c.raw_path}" for c in calls],
        )
        return persisted_count

    def _auto_extract_call_sites_if_needed(self, projects_metadata: dict[int, dict[str, Any]]) -> int:
        """Scan project source directories on disk to extract call sites if Neo4j does not have them yet."""
        extracted_total = 0
        for p_id, meta in projects_metadata.items():
            loc = meta.get("local_path")
            if not loc:
                continue
            p_dir = Path(loc)
            if not p_dir.exists() or not p_dir.is_dir():
                continue

            for ext in ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.cjs"):
                for f in p_dir.rglob(ext):
                    if any(part in f.parts for part in ("node_modules", ".venv", ".git", "dist", "build")):
                        continue
                    try:
                        content = f.read_bytes()
                        rel_path = str(f.relative_to(p_dir))
                        count = self.extract_and_persist_file_calls(
                            project_id=p_id,
                            file_path=rel_path,
                            file_bytes=content,
                        )
                        extracted_total += count
                    except Exception as e:
                        logger.debug("Failed to auto-extract calls from %s: %s", f, e)

        return extracted_total

    async def _resolve_workspace_projects(self, workspace_id: int) -> dict[int, dict[str, Any]]:
        """Fetch all projects belonging to the workspace from PostgreSQL with fallback to Neo4j."""
        metadata: dict[int, dict[str, Any]] = {}
        try:
            from app.core.postgres import database
            from app.model.project import Project
            from app.model.branch import Branch
            from app.model.repository import Repository
            from app.model.workspace_branch import WorkspaceBranch
            from sqlalchemy import select, or_

            async with database.async_session_factory() as session:
                stmt = (
                    select(Project, Branch, Repository)
                    .join(Branch, Project.branch_id == Branch.id)
                    .join(Repository, Branch.repository_id == Repository.id)
                    .where(
                        or_(
                            Project.workspace_id == workspace_id,
                            Branch.id.in_(
                                select(WorkspaceBranch.branch_id).where(
                                    WorkspaceBranch.workspace_id == workspace_id
                                )
                            ),
                        )
                    )
                )
                res = await session.execute(stmt)
                for proj, branch, repo in res.all():
                    local_dir = None
                    if branch.local_path:
                        local_dir = str(Path(branch.local_path) / proj.root_dir)

                    metadata[proj.id] = {
                        "project_id": proj.id,
                        "project_name": proj.root_dir or repo.name,
                        "branch_id": branch.id,
                        "repo_id": repo.id,
                        "repo_name": repo.name,
                        "local_path": local_dir,
                    }
                if metadata:
                    logger.info(
                        "[Cross-Repo] Resolved %d project(s) from PostgreSQL for Workspace %d: %s",
                        len(metadata),
                        workspace_id,
                        {pid: f"{m['repo_name']}:{m['project_name']}" for pid, m in metadata.items()},
                    )
        except Exception as e:
            logger.warning("[Cross-Repo] Could not query PostgreSQL workspace metadata: %s", e)

        # Fallback: If Postgres returned no projects or was inaccessible, discover all Projects from Neo4j directly
        if not metadata:
            logger.info(
                "[Cross-Repo] Discovering Project nodes directly from Neo4j (workspace %d)...",
                workspace_id,
            )
            try:
                neo_projects, _ = db.cypher_query("MATCH (p:Project) RETURN p.uid, p.name")
                for row in neo_projects:
                    p_uid = row[0]
                    p_name = row[1] if len(row) > 1 and row[1] else f"project_{p_uid}"
                    metadata[p_uid] = {
                        "project_id": p_uid,
                        "project_name": p_name,
                        "branch_id": 0,
                        "repo_id": p_uid,
                        "repo_name": f"repo_{p_uid}",
                        "local_path": None,
                    }
                logger.info(
                    "[Cross-Repo] Found %d Project node(s) in Neo4j: %s",
                    len(metadata),
                    list(metadata.keys()),
                )
            except Exception as e:
                logger.error("[Cross-Repo] Failed to query projects from Neo4j: %s", e)

        return metadata

    async def match_and_link_workspace(self, workspace_id: int) -> WorkspaceCrossRepoSummary:
        """Executes cross-repo matching across all projects in a workspace.
        
        Applies Caller-Local Floor to prevent local calls from linking cross-repo.
        """
        logger.info("================================================================================")
        logger.info("[Cross-Repo] Starting Cross-Repo HTTP Matching for Workspace ID: %d", workspace_id)

        summary = WorkspaceCrossRepoSummary(workspace_id=workspace_id)
        projects_metadata = await self._resolve_workspace_projects(workspace_id)
        project_ids = list(projects_metadata.keys())

        if not project_ids:
            logger.warning("[Cross-Repo] No projects found in workspace %d (Postgres & Neo4j). Aborting matching.", workspace_id)
            logger.info("================================================================================")
            return summary

        # 1. Fetch all call sites belonging to these projects
        query_calls = """
        MATCH (p:Project)-[:CONTAINS_CALL]->(c:HttpCallSite)
        WHERE p.uid IN $project_ids
        OPTIONAL MATCH (fn:Function)-[:MAKES_HTTP_CALL]->(c)
        RETURN c.uid AS call_uid,
               c.method AS method,
               c.raw_path AS raw_path,
               c.canonical_path AS canonical_path,
               c.file_path AS file_path,
               c.caller_name AS caller_name,
               p.uid AS project_id,
               fn.uid AS func_uid,
               fn.name AS func_name
        """
        calls_res, _ = db.cypher_query(query_calls, {"project_ids": project_ids})

        # If Neo4j has 0 call sites, attempt auto-extracting from project files on disk
        if not calls_res:
            logger.info("[Cross-Repo] 0 call sites found in Neo4j. Auto-scanning project files on disk...")
            auto_count = self._auto_extract_call_sites_if_needed(projects_metadata)
            if auto_count > 0:
                logger.info("[Cross-Repo] Auto-extracted and persisted %d call site(s) from disk!", auto_count)
                calls_res, _ = db.cypher_query(query_calls, {"project_ids": project_ids})

        summary.calls_scanned = len(calls_res)

        # 2. Fetch all routes belonging to these projects
        query_routes = """
        MATCH (p:Project)-[:EXPOSES]->(r:Route)
        WHERE p.uid IN $project_ids
        OPTIONAL MATCH (fn:Function)-[:HANDLES]->(r)
        RETURN r.uid AS route_uid,
               r.method AS method,
               r.path AS path,
               r.raw_path AS raw_path,
               p.uid AS project_id,
               fn.uid AS handler_func_uid,
               fn.name AS handler_name,
               r.framework AS framework
        """
        routes_res, _ = db.cypher_query(query_routes, {"project_ids": project_ids})
        summary.routes_scanned = len(routes_res)

        logger.info(
            "[Cross-Repo] Found %d outgoing call site(s) and %d server route(s) across %d project(s).",
            summary.calls_scanned,
            summary.routes_scanned,
            len(project_ids),
        )

        if not calls_res or not routes_res:
            if not calls_res:
                logger.info(
                    "[Cross-Repo] Note: Found 0 outgoing call site nodes in Neo4j. "
                    "Make sure caller repositories (e.g. repo_1) are indexed so client calls can be extracted."
                )
            if not routes_res:
                logger.info("[Cross-Repo] Note: Found 0 server route nodes in Neo4j.")
            logger.info("================================================================================")
            return summary

        # Organize routes by repo_id for fast Caller-Local Floor checks
        routes_by_repo: dict[int, list[dict[str, Any]]] = {}
        all_routes_list: list[dict[str, Any]] = []

        logger.info("[Cross-Repo] --- Server Route Registry (%d routes) ---", len(routes_res))
        for idx, row in enumerate(routes_res, start=1):
            p_id = row[4]
            p_meta = projects_metadata.get(p_id, {})
            r_data = {
                "uid": row[0],
                "method": row[1],
                "path": row[2],
                "raw_path": row[3],
                "project_id": p_id,
                "repo_id": p_meta.get("repo_id", p_id),
                "handler_func_uid": row[5],
                "handler_name": row[6],
                "framework": row[7] or "unknown",
                "repo_name": p_meta.get("repo_name", f"repo_{p_id}"),
                "project_name": p_meta.get("project_name", f"proj_{p_id}"),
            }
            all_routes_list.append(r_data)
            routes_by_repo.setdefault(r_data["repo_id"], []).append(r_data)
            logger.info(
                "  [%d] [%s] %s '%s' (Repo: %s, Project: %s, Handler: %s)",
                idx,
                r_data["framework"],
                r_data["method"],
                r_data["path"],
                r_data["repo_name"],
                r_data["project_name"],
                r_data["handler_name"] or "anonymous",
            )

        logger.info("[Cross-Repo] --- Evaluating Outgoing Call Sites (%d calls) ---", len(calls_res))

        # 3. Process each call site
        for idx, call_row in enumerate(calls_res, start=1):
            call_uid = call_row[0]
            call_method = call_row[1]
            call_raw_path = call_row[2]
            call_canonical_path = call_row[3]
            call_file = call_row[4]
            caller_name = call_row[5] or "anonymous"
            caller_project_id = call_row[6]
            caller_func_uid = call_row[7]
            caller_func_name = call_row[8] or caller_name

            caller_meta = projects_metadata.get(caller_project_id, {})
            caller_repo_id = caller_meta.get("repo_id", caller_project_id)
            caller_repo_name = caller_meta.get("repo_name", f"repo_{caller_project_id}")
            caller_proj_name = caller_meta.get("project_name", f"proj_{caller_project_id}")

            logger.info(
                "  [Call %d/%d] %s '%s' [canonical: '%s'] in Repo '%s' (%s :: %s)",
                idx,
                len(calls_res),
                call_method,
                call_raw_path,
                call_canonical_path,
                caller_repo_name,
                call_file,
                caller_func_name,
            )

            # --- CALLER-LOCAL FLOOR ENFORCEMENT ---
            local_repo_routes = routes_by_repo.get(caller_repo_id, [])
            local_match_route = None
            for local_r in local_repo_routes:
                if is_method_match(call_method, local_r["method"]) and is_segment_match(
                    call_canonical_path, local_r["path"]
                ):
                    local_match_route = local_r
                    break

            if local_match_route:
                summary.local_calls_filtered += 1
                logger.info(
                    "    --> [LOCAL FLOOR ACTIVE] Handled locally by Route %s '%s' in same repo '%s'. Skipped cross-repo matching.",
                    local_match_route["method"],
                    local_match_route["path"],
                    caller_repo_name,
                )
                continue

            # --- CROSS-REPO ROUTE MATCHING ---
            match_found_for_call = False
            for target_r in all_routes_list:
                # Target must be in a different repository
                if target_r["repo_id"] == caller_repo_id:
                    continue

                if is_method_match(call_method, target_r["method"]) and is_segment_match(
                    call_canonical_path, target_r["path"]
                ):
                    rule_level = determine_rule_level(call_canonical_path, target_r["path"])
                    match_found_for_call = True

                    logger.info(
                        "    --> [MATCH FOUND: %s] Target Route: %s '%s' in Repo '%s' (Project: %s, Handler: %s)",
                        rule_level.upper(),
                        target_r["method"],
                        target_r["path"],
                        target_r["repo_name"],
                        target_r["project_name"],
                        target_r["handler_name"] or "anonymous",
                    )

                    # 1. Link (HttpCallSite)-[:MATCHES_ROUTE]->(Route)
                    link_call_cypher = """
                    MATCH (c:HttpCallSite {uid: $call_uid})
                    MATCH (r:Route {uid: $route_uid})
                    MERGE (c)-[m:MATCHES_ROUTE]->(r)
                    ON CREATE SET m.rule_level = $rule_level, m.matched_at = timestamp()
                    """
                    db.cypher_query(link_call_cypher, {
                        "call_uid": call_uid,
                        "route_uid": target_r["uid"],
                        "rule_level": rule_level,
                    })

                    # 2. Link (Function)-[:CROSS_HTTP_CALLS]->(Route) if caller function exists
                    if caller_func_uid:
                        link_func_cypher = """
                        MATCH (fn:Function {uid: $func_uid})
                        MATCH (r:Route {uid: $route_uid})
                        MERGE (fn)-[cr:CROSS_HTTP_CALLS {method: $method, call_path: $call_path}]->(r)
                        ON CREATE SET cr.rule_level = $rule_level, cr.matched_at = timestamp()
                        """
                        db.cypher_query(link_func_cypher, {
                            "func_uid": caller_func_uid,
                            "route_uid": target_r["uid"],
                            "method": call_method,
                            "call_path": call_raw_path,
                            "rule_level": rule_level,
                        })
                        logger.info(
                            "    --> Linked in Graph: (fn:Function '%s') -[:CROSS_HTTP_CALLS]-> (r:Route '%s')",
                            caller_func_name,
                            target_r["path"],
                        )

                    match_result = CrossRepoMatchResult(
                        caller_project_id=caller_project_id,
                        caller_func_uid=caller_func_uid,
                        caller_func_name=caller_func_name,
                        caller_file=call_file,
                        call_path=call_raw_path,
                        method=call_method,
                        target_project_id=target_r["project_id"],
                        target_route_uid=target_r["uid"],
                        target_route_path=target_r["path"],
                        target_handler_name=target_r["handler_name"],
                        rule_level=rule_level,
                    )
                    summary.details.append(match_result)
                    summary.links_created += 1

            if not match_found_for_call:
                logger.info("    --> [NO MATCH] No route matching '%s' found in other repositories.", call_canonical_path)

        logger.info("================================================================================")
        logger.info("[Cross-Repo] MATCHING FINISHED for Workspace %d:", workspace_id)
        logger.info("  * Total Calls Scanned:       %d", summary.calls_scanned)
        logger.info("  * Total Server Routes:       %d", summary.routes_scanned)
        logger.info("  * Local In-Repo Filtered:    %d", summary.local_calls_filtered)
        logger.info("  * Cross-Repo Links Created:  %d", summary.links_created)
        logger.info("================================================================================")
        return summary

    async def get_cross_repo_links_for_workspace(self, workspace_id: int) -> list[dict[str, Any]]:
        """Query all established cross-repo links in the workspace."""
        projects_metadata = await self._resolve_workspace_projects(workspace_id)
        project_ids = list(projects_metadata.keys())
        if not project_ids:
            return []

        cypher = """
        MATCH (pA:Project)-[:CONTAINS_CALL]->(c:HttpCallSite)-[m:MATCHES_ROUTE]->(r:Route)<-[:EXPOSES]-(pB:Project)
        WHERE pA.uid IN $project_ids AND pB.uid IN $project_ids
        OPTIONAL MATCH (fnCaller:Function)-[:MAKES_HTTP_CALL]->(c)
        OPTIONAL MATCH (fnHandler:Function)-[:HANDLES]->(r)
        RETURN c.file_path AS caller_file,
               c.caller_name AS caller_func_name,
               fnCaller.uid AS caller_func_uid,
               c.method AS method,
               c.raw_path AS call_path,
               c.canonical_path AS call_canonical_path,
               c.client_library AS client_library,
               r.path AS target_route_path,
               r.framework AS target_framework,
               fnHandler.name AS target_handler_name,
               fnHandler.uid AS target_handler_uid,
               m.rule_level AS rule_level,
               pA.uid AS caller_proj_id,
               pB.uid AS target_proj_id
        """
        results, _ = db.cypher_query(cypher, {"project_ids": project_ids})
        links = []
        for row in results:
            pA_id = row[12]
            pB_id = row[13]
            metaA = projects_metadata.get(pA_id, {})
            metaB = projects_metadata.get(pB_id, {})
            links.append({
                "caller_repo": metaA.get("repo_name", f"repo_{pA_id}"),
                "caller_project": metaA.get("project_name", f"project_{pA_id}"),
                "caller_file": row[0],
                "caller_func_name": row[1],
                "caller_func_uid": row[2],
                "method": row[3],
                "call_path": row[4],
                "call_canonical_path": row[5],
                "client_library": row[6],
                "target_repo": metaB.get("repo_name", f"repo_{pB_id}"),
                "target_project": metaB.get("project_name", f"project_{pB_id}"),
                "target_route_path": row[7],
                "target_framework": row[8],
                "target_handler_name": row[9],
                "target_handler_uid": row[10],
                "rule_level": row[11],
            })
        return links

    async def clear_cross_repo_links(self, workspace_id: int) -> int:
        """Deletes all MATCHES_ROUTE and CROSS_HTTP_CALLS relationships within the workspace."""
        projects_metadata = await self._resolve_workspace_projects(workspace_id)
        project_ids = list(projects_metadata.keys())
        if not project_ids:
            return 0

        cypher = """
        MATCH (p:Project)-[:CONTAINS_CALL]->(c:HttpCallSite)-[m:MATCHES_ROUTE]->(r:Route)
        WHERE p.uid IN $project_ids
        DELETE m
        """
        db.cypher_query(cypher, {"project_ids": project_ids})

        cypher_func = """
        MATCH (p:Project)-[:INCLUDES]->(:File)-[:CONTAINS*1..5]->(fn:Function)-[cr:CROSS_HTTP_CALLS]->(r:Route)
        WHERE p.uid IN $project_ids
        DELETE cr
        """
        db.cypher_query(cypher_func, {"project_ids": project_ids})
        logger.info("[Cross-Repo] Cleared all existing cross-repo links for workspace %d", workspace_id)
        return 1


_SERVICE = CrossRepoService()


def get_cross_repo_service() -> CrossRepoService:
    return _SERVICE
