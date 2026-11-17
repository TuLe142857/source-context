from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(
        description=(
            "WORKSPACE-WIDE SEMANTIC SEARCH: Search across all repositories and branches in a workspace "
            "using AI vector embeddings (Voyage AI). Use this when you do not know which repository contains "
            "the desired functionality, concept, or feature."
        )
    )
    async def search_in_workspace(
        client: ApiClientDep,
        query: Annotated[
            str,
            Field(
                description=(
                    "Natural language query describing the desired concept, feature, or logic "
                    "(e.g. 'user authentication and session verification', 'generate password reset email')."
                )
            ),
        ],
        workspace_id: Annotated[int, Field(ge=1, description="Workspace ID.")],
        top_k: Annotated[
            int, Field(default=5, ge=1, le=50, description="Number of top matching code chunks to return.")
        ],
    ) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{workspace_id}", req_body)
        raw_results = res.result()

        if isinstance(raw_results, list):
            pruned: list[dict[str, Any]] = []
            for item in raw_results:
                if isinstance(item, dict):
                    raw_doc = item.get("docstring")
                    doc = (raw_doc[:300] + "...") if raw_doc and len(raw_doc) > 300 else raw_doc
                    pruned.append(
                        {
                            "node_id": item.get("node_id"),
                            "name": item.get("name"),
                            "kind": item.get("kind"),
                            "file_path": item.get("file_path"),
                            "signature": item.get("signature"),
                            "score": round(float(item.get("score", 0.0)), 4),
                            "summary": item.get("summary"),
                            "docstring": doc,
                        }
                    )
                else:
                    pruned.append(item)
            return pruned

        return raw_results

    @mcp.tool(
        description=(
            "PRIMARY SEMANTIC CODE SEARCH: Search for functions, methods, classes, and logic by what they DO "
            "or what CONCEPT they implement, using AI dense vector embeddings (Voyage AI). "
            "ALWAYS use this tool FIRST when asked to locate, find, or identify code based on natural language "
            "descriptions, business requirements, or technical features (e.g. 'find functions responsible for "
            "generating and verifying password-reset JWT tokens', 'authenticate user credentials', "
            "'render email template') whenever the exact file path or function name is not specified. "
            "Returns top matching code snippets with their file locations, signatures, and similarity scores."
        )
    )
    async def search_in_repo_and_branch(
        client: ApiClientDep,
        query: Annotated[
            str,
            Field(
                description=(
                    "Natural language query describing the feature, concept, or technical behavior to find "
                    "(e.g. 'generating and verifying password-reset JWT tokens', 'authenticate user password')."
                )
            ),
        ],
        repository_id: Annotated[int, Field(ge=1, description="Repository ID to search within.")],
        branch_name: Annotated[
            str,
            Field(default="master", description="Git branch name (defaults to 'master')."),
        ] = "master",
        top_k: Annotated[
            int,
            Field(default=5, ge=1, le=50, description="Number of top matching code chunks to return."),
        ] = 5,
    ) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{repository_id}/{branch_name}", req_body)
        raw_results = res.result()

        # Prune duplicated raw payloads to prevent tool output buffer truncation (>10k chars)
        if isinstance(raw_results, list):
            pruned: list[dict[str, Any]] = []
            for item in raw_results:
                if isinstance(item, dict):
                    raw_doc = item.get("docstring")
                    doc = (raw_doc[:300] + "...") if raw_doc and len(raw_doc) > 300 else raw_doc
                    pruned.append(
                        {
                            "node_id": item.get("node_id"),
                            "name": item.get("name"),
                            "kind": item.get("kind"),
                            "file_path": item.get("file_path"),
                            "signature": item.get("signature"),
                            "score": round(float(item.get("score", 0.0)), 4),
                            "summary": item.get("summary"),
                            "docstring": doc,
                        }
                    )
                else:
                    pruned.append(item)
            return pruned

        return raw_results
