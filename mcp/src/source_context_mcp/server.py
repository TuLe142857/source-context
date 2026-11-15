from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server import MCPServer

from source_context_mcp.core import ApiClient, AppContext, get_settings_with_overrides
from source_context_mcp.core.metadata import get_package_version
from source_context_mcp.prompts import register_prompts
from source_context_mcp.resources import register_resources
from source_context_mcp.tools import register_tools

SERVER_DESCRIPTION = """
SourceContextMCP is an MCP server that gives AI coding assistants structured, queryable access to indexed source code \
across workspaces, repositories, branches, and projects. It exposes tools to browse project/file structure, read file \
and code-node content, traverse call/reference graphs between code nodes, and run semantic (vector) search over a \
codebase — letting an agent explore and understand large, multi-repository codebases without needing direct local file \
access."
"""

SERVER_INSTRUCTIONS = (
    "SourceContextMCP provides intelligent, pre-indexed access to codebases, call graphs, AST structures, "
    "and AI vector semantic search.\n\n"
    "Core Guidelines:\n"
    "1. Semantic Search for Concepts: ALWAYS use search_in_repo_and_branch first when asked to locate or identify "
    "functions/classes by what they DO or what feature they implement, "
    "whenever exact file or symbol names are not given.\n"
    "2. File Outlines: Use get_file_structure(file='path/or/name') to inspect classes, functions, signatures, "
    "and docstrings of a specific file once the file name/path is known.\n"
    "3. Impact Analysis: Use analyze_impact(symbol='name') for one-shot impact analysis (callers, call lines, callees, "
    "affected files) to assess blast radius in a single call.\n"
    "4. Callers & Callees: Use find_node_usages(symbol='name') to find callers, and find_node_callees(symbol='name') "
    "to find internal functions/utilities called.\n"
    "5. Read Raw Source Code: Use get_file_content(file='path/or/name') only when you need "
    "the exact raw implementation body.\n"
    "6. Scope: Pass pre-resolved repository_id and branch directly; do not call listing tools when scope is known.\n"
    "7. Trust Graph & Vector Results: Use tool results directly. "
    "Do not repeatedly download raw file contents to manually grep.\n"
)


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

    Args:
        base_url_override: override default server URL
        pat_override: override default Personal Access Token
        workspace_id_override: override default workspace ID
    """

    life_span = make_life_span(
        base_url_override=base_url_override, pat_override=pat_override, workspace_id_override=workspace_id_override
    )

    server = MCPServer(
        name="source-context-mcp",
        lifespan=life_span,
        version=get_package_version(),
        description=SERVER_DESCRIPTION,
        instructions=SERVER_INSTRUCTIONS,
    )

    register_tools(server)
    register_resources(server)
    register_prompts(server)

    return server
