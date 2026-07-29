from mcp.server import MCPServer

from .debug import register_tools as register_debug_tools
from .workspace import register_tools as register_workspace_tools


def register_tools(mcp: MCPServer) -> None:
    """
    Registry tools for MCPServer.
    Args:
        mcp: instance of MCPServer
    """
    register_workspace_tools(mcp)
    register_debug_tools(mcp)
