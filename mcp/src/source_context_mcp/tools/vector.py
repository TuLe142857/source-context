import asyncio
import logging
from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from source_context_mcp.core import ApiClientDep
from source_context_mcp.core.api_client import ApiClient

logger = logging.getLogger(__name__)


async def _fetch_node_snippet(client: ApiClient, node_id: str | None) -> str | None:
    """Safely retrieves the source code snippet of a node via the graph API.

    Args:
        client (ApiClient): The API client.
        node_id (str | None): The node ID.

    Returns:
        str | None: The code snippet if found, else None.
    """
    if not node_id:
        return None
    try:
        res = await client.get(f"/graph/nodes/{node_id}/content")
        if res.success and isinstance(res.data, str):
            return res.data
        return None
    except Exception as exc:
        logger.debug("Failed to fetch snippet for node %s: %s", node_id, exc)
        return None


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(
        description=(
            "SEMANTIC CODE SEARCH WITH IMPLEMENTATION SNIPPETS: Search for functions, methods, and classes "
            "by what they DO or how they work, returning their ACTUAL SOURCE CODE SNIPPETS directly. "
            "USE THIS TOOL WHEN: You need to understand implementation logic, verify validation rules, "
            "explain algorithms, or see how a feature is coded without making follow-up file-reading calls. "
            "DO NOT call get_node_content or read_file after using this tool, as the complete implementation "
            "is already provided in `code_snippet`."
        )
    )
    async def search_code_snippets(
        client: ApiClientDep,
        query: Annotated[
            str,
            Field(
                description=(
                    "Natural language query describing the feature, concept, or technical behavior to find "
                    "(e.g. 'generating and validating password reset tokens with HMAC', 'verify user password')."
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

        if not isinstance(raw_results, list):
            return raw_results

        # Concurrently fetch source code snippets for all matched nodes
        node_ids = [
            str(item["node_id"]) if isinstance(item, dict) and item.get("node_id") else None for item in raw_results
        ]
        snippets = await asyncio.gather(*[_fetch_node_snippet(client, nid) for nid in node_ids])

        results: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_results):
            if isinstance(item, dict):
                results.append(
                    {
                        "node_id": item.get("node_id"),
                        "name": item.get("name"),
                        "kind": item.get("kind"),
                        "file_path": item.get("file_path"),
                        "score": round(float(item.get("score", 0.0)), 4),
                        "code_snippet": snippets[idx] or "",
                    }
                )
            else:
                results.append(item)

        return results

    @mcp.tool(
        description=(
            "FAST SYMBOL LOCATION & METADATA SEARCH: Fast, lightweight semantic search to locate symbols "
            "and retrieve their `node_id`, `name`, and `file_path` WITHOUT loading source code snippets. "
            "USE THIS TOOL WHEN: You need an intermediate stepping stone—such as finding a `node_id` to pass into "
            "`analyze_impact` or `find_node_usages`, or quickly checking which file defines a concept. "
            "DO NOT use this tool if you need to read or explain implementation code (use `search_code_snippets`)."
        )
    )
    async def search_symbols_metadata(
        client: ApiClientDep,
        query: Annotated[
            str,
            Field(
                description=(
                    "Natural language query describing the symbol, concept, or feature to locate "
                    "(e.g. 'password reset token generator', 'authenticate user credentials')."
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
            Field(default=5, ge=1, le=50, description="Number of top matching symbols to return."),
        ] = 5,
    ) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{repository_id}/{branch_name}", req_body)
        raw_results = res.result()

        if isinstance(raw_results, list):
            metadata_results: list[dict[str, Any]] = []
            for item in raw_results:
                if isinstance(item, dict):
                    metadata_results.append(
                        {
                            "node_id": item.get("node_id"),
                            "name": item.get("name"),
                            "kind": item.get("kind"),
                            "file_path": item.get("file_path"),
                            "score": round(float(item.get("score", 0.0)), 4),
                        }
                    )
                else:
                    metadata_results.append(item)
            return metadata_results

        return raw_results

    @mcp.tool(
        description=(
            "PRIMARY SEMANTIC CODE SEARCH (ALIAS FOR search_code_snippets): Search for functions, methods, "
            "and classes by what they DO or how they work, returning their ACTUAL SOURCE CODE SNIPPETS directly. "
            "DO NOT call get_node_content or read_file after using this tool, as the complete implementation "
            "is already provided in `code_snippet`."
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
        return await search_code_snippets(
            client=client,
            query=query,
            repository_id=repository_id,
            branch_name=branch_name,
            top_k=top_k,
        )

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
            results: list[dict[str, Any]] = []
            for item in raw_results:
                if isinstance(item, dict):
                    results.append(
                        {
                            "node_id": item.get("node_id"),
                            "name": item.get("name"),
                            "kind": item.get("kind"),
                            "file_path": item.get("file_path"),
                            "score": round(float(item.get("score", 0.0)), 4),
                        }
                    )
                else:
                    results.append(item)
            return results

        return raw_results
