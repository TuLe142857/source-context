from typing import Any

from mcp.server import MCPServer

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:
    """
    Registers all the vector tools.
    Args:
        mcp: MCP server instance
    """

    @mcp.tool()
    async def search_in_workspace(client: ApiClientDep, query: str, workspace_id: int, top_k: int = 5) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{workspace_id}", req_body)

        return res.data

    @mcp.tool()
    async def search_in_repo_and_branch(
        client: ApiClientDep, repository_id: int, branch_name: str, query: str, top_k: int = 5
    ) -> Any:
        req_body = {
            "query": query,
            "top_k": top_k,
        }

        res = await client.post(f"/vector/search/{repository_id}/{branch_name}", req_body)

        return res.data
