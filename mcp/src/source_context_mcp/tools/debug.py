from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from source_context_mcp.core import AppContext, Settings
from source_context_mcp.core.metadata import get_package_version


def register_tools(mcp: MCPServer):
    """
     Register development-only MCP tools.

    These tools are registered only when the package version is a
    development release (e.g. ``0.1.0.dev1``). They are excluded from
    alpha, beta, release candidate, and stable builds.

    Args:
        mcp: The MCP server instance to register tools with.
    """

    version = get_package_version()
    if "dev" not in version:
        return

    @mcp.tool(description="Show current server configuration. For development use only.")
    def debug(ctx: Context[AppContext]) -> Settings:
        app_context: AppContext = ctx.request_context.lifespan_context
        return app_context.settings
