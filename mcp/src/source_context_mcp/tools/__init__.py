from mcp.server import MCPServer

from .base import register_tools as register_base_tools
from .debug import register_tools as register_debug_tools
from .graph import register_tools as register_graph_tools
from .vector import register_tools as register_vector_tools


def register_tools(mcp: MCPServer) -> None:
    """
    Registry tools for MCPServer.
    Args:
        mcp: instance of MCPServer
    """
    register_debug_tools(mcp)

    register_base_tools(mcp)
    register_graph_tools(mcp)
    register_vector_tools(mcp)
