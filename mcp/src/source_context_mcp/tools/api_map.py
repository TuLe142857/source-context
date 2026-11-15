from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(
        description="List API endpoints (e.g. REST routes) served by a project: signature, handler node, number of "
        "calls resolved to it, and protocol-specific `details` (REST: http_method, path, path_params). "
        "Use `handler_node_id` with get_node_content or find_node_usages."
    )
    async def list_api_endpoints_in_project(
        client: ApiClientDep,
        project_id: Annotated[str, Field(description="Project ID.")],
    ) -> Any:
        res = await client.get(f"/api-map/projects/{project_id}/endpoints")
        return res.result()

    @mcp.tool(
        description="List outgoing API calls (e.g. HTTP requests) made by a project: signature, call node, target "
        "host, protocol-specific `details` (REST: http_method, path), and `targets` - the endpoints each call "
        "resolves to, possibly in other projects (empty when unresolved)."
    )
    async def list_api_calls_in_project(
        client: ApiClientDep,
        project_id: Annotated[str, Field(description="Project ID.")],
    ) -> Any:
        res = await client.get(f"/api-map/projects/{project_id}/calls")
        return res.result()
