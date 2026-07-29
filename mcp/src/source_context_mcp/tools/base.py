from typing import Any

from mcp.server import MCPServer

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:
    """
    Register bases tools:
        - list user's available workspaces
        - list repos in workspace
        - list branches in repo
        - list projects in branch

    Args:
        mcp: MCPServer instance
    """

    @mcp.tool(description="List all available workspaces that current user can access")
    async def list_workspaces(client: ApiClientDep) -> Any:
        res = await client.get("/general/workspaces", response_model=list)
        return res.data

    @mcp.tool(description="List all available repositories in workspace")
    async def list_repositories(
        client: ApiClientDep,
        workspace_id: int,
    ) -> Any:
        res = await client.post("/general/repositories", {"workspace_id": workspace_id})
        return res.data

    @mcp.tool(description="List all available branches in specified repository.")
    async def list_branches(client: ApiClientDep, project_id: int) -> Any:
        """This tool is not implemented yet"""
        return ["This tool is not implemented yet"]

    @mcp.tool(description="List all available projects in specific branch.")
    def list_projects(client: ApiClientDep, branch_id: int) -> Any:
        """This tool is not implemented yet"""
        return ["This tool is not implemented yet"]
