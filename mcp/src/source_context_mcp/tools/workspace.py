from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Resolve


def get_name() -> str:
    return "me"


DefaultDep = Annotated[str, Resolve(get_name)]


def register_tools(mcp: MCPServer) -> None:
    """
    Register workspace tools
    Args:
        mcp: MCPServer instance
    """

    @mcp.tool()
    def list_workspace(name: DefaultDep) -> list[str]:
        return ["wk1", "wk2", name]
