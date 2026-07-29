from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from source_context_mcp.core import AppContext, Settings


def register_tools(mcp: MCPServer):
    @mcp.tool(description="This tool for development env only. Show all current config. Read source code to see more")
    def debug(ctx: Context[AppContext]) -> Settings:
        app_context: AppContext = ctx.request_context.lifespan_context
        return app_context.settings
