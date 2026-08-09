from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(description="Semantic search across all repositories and branches in a workspace.")
    async def search_in_workspace(
        client: ApiClientDep,
        query: Annotated[str, Field(description="Query to search in workspace.")],
        workspace_id: Annotated[int, Field(ge=1, description="Workspace ID.")],
        top_k: Annotated[int, Field(default=5, ge=1, le=50, description="Number of top results to return.")],
    ) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{workspace_id}", req_body)

        return res.result()

    @mcp.tool(description="Semantic search scoped to a specific repository and branch.")
    async def search_in_repo_and_branch(
        client: ApiClientDep,
        repository_id: Annotated[int, Field(ge=1, description="Repository ID.")],
        branch_name: Annotated[str, Field(description="Branch name.")],
        query: Annotated[str, Field(description="Query to search in branch scope.")],
        top_k: Annotated[int, Field(default=5, ge=1, le=50, description="Number of top results to return.")],
    ) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{repository_id}/{branch_name}", req_body)

        return res.result()
