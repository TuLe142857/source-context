from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import Field

from source_context_mcp.core import ApiClientDep, AppContext


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(description="List all workspaces accessible to the current user.")
    async def list_workspaces(client: ApiClientDep) -> Any:
        res = await client.get("/general/workspaces", response_model=list)
        return res.result()

    @mcp.tool(description="Get default workspace and repository settings configured for a local path.")
    async def get_path_settings(
        ctx: Context[AppContext],
        path: Annotated[str, Field(description="Local directory path to look up default settings for.")],
    ) -> dict[str, Any]:
        app_context: AppContext = ctx.request_context.lifespan_context
        settings = app_context.settings
        return {
            "path": path,
            "default_workspace_id": settings.PATH_WORKSPACE.get(path, None),
            "default_repo_id": settings.PATH_REPO.get(path, None),
        }

    @mcp.tool(
        description="Get the server-configured default workspace ID, used when the current path has no path-specific "
        "default."
    )
    async def default_workspace(ctx: Context[AppContext]) -> Any:
        app_context: AppContext = ctx.request_context.lifespan_context
        return app_context.settings.DEFAULT_WORKSPACE_ID

    @mcp.tool(description="List all repositories in a workspace.")
    async def list_repositories(
        client: ApiClientDep,
        workspace_id: Annotated[int, Field(description="Workspace ID.", ge=1)],
    ) -> Any:
        res = await client.post("/general/repositories", {"workspace_id": workspace_id})
        return res.result()

    @mcp.tool(description="List all branches in a repository.")
    async def list_branches(
        client: ApiClientDep,
        workspace_id: Annotated[int, Field(description="Workspace ID.", ge=1)],
        repository_id: Annotated[int, Field(description="Repository ID.", ge=1)],
    ) -> Any:
        req_body = {
            "workspace_id": workspace_id,
            "repository_id": repository_id,
        }
        res = await client.post("/general/branches", req_body)
        return res.result()

    @mcp.tool(description="List all projects on a branch.")
    async def list_projects(
        client: ApiClientDep,
        workspace_id: Annotated[int, Field(description="Workspace ID.", ge=1)],
        repository_id: Annotated[int, Field(description="Repository ID.", ge=1)],
        branch_name: Annotated[str, Field(description="Branch name.")],
    ) -> Any:
        req_body = {
            "workspace_id": workspace_id,
            "repo_id": repository_id,
            "branch_name": branch_name,
        }
        res = await client.post("/general/projects", req_body)
        return res.result()
