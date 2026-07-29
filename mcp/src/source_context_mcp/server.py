from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server import MCPServer

from source_context_mcp.core import ApiClient, AppContext, get_settings_with_overrides
from source_context_mcp.tools import register_tools


def make_life_span(
    base_url_override: str | None = None, pat_override: str | None = None, workspace_id_override: int | None = None
):
    @asynccontextmanager
    async def server_lifespan(app: MCPServer) -> AsyncIterator[AppContext]:
        settings = get_settings_with_overrides(
            server_url_override=base_url_override,
            pat_override=pat_override,
            default_workspace_id_override=workspace_id_override,
        )

        yield AppContext(
            api_client=ApiClient(base_url=settings.SERVER_URL, token=settings.PAT.get_secret_value()), settings=settings
        )

    return server_lifespan


def create_server(
    base_url_override: str | None = None, pat_override: str | None = None, workspace_id_override: int | None = None
) -> MCPServer:
    """
    Create an MCPServer instance.
    Returns:
        MCPServer instance.
    """

    life_span = make_life_span(
        base_url_override=base_url_override, pat_override=pat_override, workspace_id_override=workspace_id_override
    )

    server = MCPServer(
        name="SourceContextMCP",
        lifespan=life_span,
    )

    register_tools(server)

    return server


mcp = create_server()
