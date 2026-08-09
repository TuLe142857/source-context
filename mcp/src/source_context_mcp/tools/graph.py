from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from pydantic import Field

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(description="List all files in a project.")
    async def list_files_in_project(
        client: ApiClientDep,
        project_id: Annotated[str, Field(description="Project ID.")],
    ) -> Any:
        res = await client.get(f"/graph/projects/{project_id}/files")
        return res.result()

    @mcp.tool(description="Get file structure: classes and methods.")
    async def get_file_structure(
        client: ApiClientDep,
        file_id: Annotated[str, Field(description="File ID.")],
    ) -> Any:
        res = await client.get(f"/graph/files/{file_id}/structure")
        return res.result()

    @mcp.tool(description="Read file content.")
    async def get_file_content(
        client: ApiClientDep,
        file_id: Annotated[str, Field(description="File ID.")],
    ) -> Any:
        res = await client.get(f"/graph/files/{file_id}/content")
        return res.result()

    @mcp.tool(description="Get node metadata: id, name, file_id, position in file.")
    async def get_node_info(
        client: ApiClientDep,
        node_id: Annotated[str, Field(description="Node ID.")],
    ) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}")
        return res.result()

    @mcp.tool(description="Get node source content.")
    async def get_node_content(
        client: ApiClientDep,
        node_id: Annotated[str, Field(description="Node ID.")],
    ) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}/content")
        return res.result()

    # @mcp.tool(description="This tool not implemented yet.")
    # async def find_node_by_name(
    #     client: ApiClientDep,
    #     name: Annotated[str, Field(description="The name of the node")],
    #     node_type: Annotated[
    #         Literal["type-definition", "", None],
    #         Field(default=None, description="The type of the node. Default is all types"),
    #     ],
    # ) -> Any:
    #     return []

    @mcp.tool(description="Find all nodes that call or reference the specified node.")
    async def find_node_usages(
        client: ApiClientDep,
        node_id: Annotated[str, Field(description="Node ID.")],
    ) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}/usages")
        return res.result()

    @mcp.tool(description="Find all nodes that the specified node calls or references.")
    async def find_node_callees(
        client: ApiClientDep,
        node_id: Annotated[str, Field(description="Node ID.")],
    ) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}/callees")
        return res.result()
