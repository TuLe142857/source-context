from typing import Annotated

from mcp.server.mcpserver import Context, Resolve

from source_context_mcp.core import ApiClient, AppContext


def get_api_client(ctx: Context[AppContext]) -> ApiClient:
    app_context: AppContext = ctx.request_context.lifespan_context
    return app_context.api_client


ApiClientDep = Annotated[ApiClient, Resolve(get_api_client)]
