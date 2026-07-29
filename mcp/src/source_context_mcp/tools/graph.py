from mcp.server import MCPServer


def register_tools(mcp: MCPServer) -> None:
    """
    Registers all the graph tools.
    Args:
        mcp: MCPServer instance
    """

    @mcp.tool()
    def list_files_in_project(project_id: str) -> list[str]:
        """This tools not implemented yet."""
        return []

    @mcp.tool()
    def get_file_structure(file_id: str) -> list[str]:
        """This tools not implemented yet."""
        return []

    @mcp.tool()
    def get_file_content(file_id: str) -> list[str]:
        """This tools not implemented yet."""
        return []

    @mcp.tool()
    def get_node_info(node_id: str) -> list[str]:
        """This tools not implemented yet."""
        return []

    @mcp.tool()
    def get_node_content(node_id: str) -> str:
        """This tools not implemented yet."""
        return ""

    @mcp.tool()
    def find_node_usages(node_id: str) -> list[str]:
        """This tools not implemented yet."""
        return []

    @mcp.tool()
    def find_node_callees(node_id: str) -> list[str]:
        """This tools not implemented yet."""
        return []
