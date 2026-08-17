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

SERVER_INSTRUCTIONS = """
SourceContextMCP gives read-only access to a pre-indexed source of truth for one or more codebases, organized as: \
workspace -> repository -> branch -> project -> file -> node (class/method/function/variable/...).

Most tools require one or more IDs (workspace_id, repository_id, project_id, file_id, node_id). These are opaque and \
server-assigned - never guess them. Always obtain them from the matching listing tool or reuse an ID from a previous \
call.

Resolve scope before calling graph or search tools. Try get_path_settings(path) first if the user is working inside a \
local checkout; fall back to default_workspace() if no path-specific config exists. Otherwise narrow down with \
list_workspaces -> list_repositories -> list_branches -> list_projects.

Once you have a project_id, use list_files_in_project for file_ids, then get_file_structure before get_file_content \
when you only need an overview or a node_id - avoid reading full file contents unless necessary.

For call-graph relationships on a node_id: use find_node_usages before renaming or changing a signature to assess \
blast radius, and find_node_callees to understand what a symbol depends on. Prefer graph traversal over semantic \
search when you need precise, complete relationships - semantic search is approximate and may miss or over-return \
results.

Use search_in_workspace or search_in_repo_and_branch (prefer the latter when repository/branch is already known - more \
precise) when you don't know exact file/node names. Treat semantic search as an entry point, then switch to graph \
tools for precise structured details.
"""


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
