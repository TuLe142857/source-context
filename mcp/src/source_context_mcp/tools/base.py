from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from source_context_mcp.core import ApiClientDep, AppContext


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
        return res.result()

    @mcp.tool(
        description=(
            "Get the default settings for specified directory.Include default workspace id adn default repository id."
        )
    )
    async def get_path_settings(ctx: Context[AppContext], path: str) -> dict[str, Any]:
        app_context: AppContext = ctx.request_context.lifespan_context
        settings = app_context.settings
        return {
            "path": path,
            "default_workspace_id": settings.PATH_WORKSPACE.get(path, None),
            "default_repo_id": settings.PATH_REPO.get(path, None),
        }

    @mcp.tool(
        description=(
            "Get default workspace. "
            "This is the default workspace use settings in case current path has no default config"
        )
    )
    async def default_workspace(ctx: Context[AppContext]) -> Any:
        app_context: AppContext = ctx.request_context.lifespan_context
        return app_context.settings.DEFAULT_WORKSPACE_ID

    @mcp.tool(description="List all available repositories in workspace")
    async def list_repositories(
        client: ApiClientDep,
        workspace_id: int,
    ) -> Any:
        res = await client.post("/general/repositories", {"workspace_id": workspace_id})
        return res.result()

    @mcp.tool(description="List all available branches in specified repository.")
    async def list_branches(client: ApiClientDep, workspace_id: int, repository_id: int) -> Any:
        req_body = {
            "workspace_id": workspace_id,
            "repository_id": repository_id,
        }
        res = await client.post("/general/branches", req_body)
        return res.result()

    @mcp.tool(description="List all available projects in specific branch.")
    async def list_projects(client: ApiClientDep, workspace_id: int, repository_id: int, branch_name: str) -> Any:
        req_body = {
            "workspace_id": workspace_id,
            "repo_id": repository_id,
            "branch_name": branch_name,
        }
        res = await client.post("/general/projects", req_body)
        return res.result()
