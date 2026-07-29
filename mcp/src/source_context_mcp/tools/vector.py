from mcp.server import MCPServer


def register_tools(mcp: MCPServer) -> None:
    """
    Registers all the vector tools.
    Args:
        mcp: MCP server instance
    """

    @mcp.tool()
    def search(query: str) -> list[str]:
        return ["results1", "results2"]
