from mcp.server import MCPServer

from .analyze_architecture import register_prompts as register_analyze_architecture
from .prepare_for_change import register_prompts as register_prepare_for_change
from .summarize_file import register_prompts as register_summarize_file


def register_prompts(mcp: MCPServer) -> None:
    """
    Register prompts for MCP server
    Args:
        mcp: MCPServer instance
    """
    register_analyze_architecture(mcp)
    register_prepare_for_change(mcp)
    register_summarize_file(mcp)


__all__ = ["register_prompts"]
