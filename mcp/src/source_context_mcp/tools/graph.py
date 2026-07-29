from typing import Any

from mcp.server import MCPServer

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:
    """
    Registers all the graph tools.
    Args:
        mcp: MCPServer instance
    """

    @mcp.tool(description="List all files in specified project.")
    async def list_files_in_project(client: ApiClientDep, project_id: str) -> Any:
        res = await client.get(f"/graph/projects/{project_id}/files")
        return res.data

    @mcp.tool(description="Inspect file structure(classes and methods")
    async def get_file_structure(client: ApiClientDep, file_id: str) -> Any:
        res = await client.get(f"/graph/files/{file_id}/structures")
        return res.data

    @mcp.tool(description="Read file content.")
    async def get_file_content(client: ApiClientDep, file_id: str) -> Any:
        res = await client.get(f"/graph/files/{file_id}/content")
        return res.data

    @mcp.tool(description="Find all nodes that call/reference to the specified node.")
    async def find_node_usages(client: ApiClientDep, node_id: str) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}/usages")
        return res.data

    @mcp.tool(description="Find all nodes(or its children) that the specified node is calling or reference to.")
    async def find_node_callees(client: ApiClientDep, node_id: str) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}/callees")
        return res.data
