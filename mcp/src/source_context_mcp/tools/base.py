from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from source_context_mcp.core import AppContext


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

    @mcp.tool()
    def list_workspaces(ctx: Context[AppContext]) -> list[str]:
        """This tool is not implemented yet"""

        app_context: AppContext = ctx.request_context.lifespan_context
        api_client = app_context.api_client

        return ["wk1", "wk2"]

    @mcp.tool()
    def list_repositories() -> list[str]:
        """This tool is not implemented yet"""
        return ["repo1", "repo2"]

    @mcp.tool()
    def list_branches() -> list[str]:
        """This tool is not implemented yet"""
        return ["branch1", "branch2"]

    @mcp.tool()
    def list_projects() -> list[str]:
        """This tool is not implemented yet"""
        return ["project1", "project2"]
