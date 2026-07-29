from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Context, Resolve

from source_context_mcp.core import AppContext, Settings


class Calculator:
    def calc_sum(self, a: int | float, b: int | float) -> int | float:
        return a + b


def get_calculator() -> Calculator:
    return Calculator()


def register_tools(mcp: MCPServer):
    @mcp.tool(description="This tool for development env only. Show all current config. Read source code to see more")
    def debug(ctx: Context[AppContext]) -> Settings:
        app_context: AppContext = ctx.request_context.lifespan_context
        return app_context.settings

    @mcp.tool(description="This tool for test MCP Resolver.(Similar to FastAPI Dependencies)")
    def calc_sum(
        a: int | float, b: int | float, calculator: Annotated[Calculator, Resolve(get_calculator)]
    ) -> int | float:
        return calculator.calc_sum(a, b)
