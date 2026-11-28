from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from source_context_mcp.core import ApiClientDep


def register_tools(mcp: MCPServer) -> None:

    @mcp.tool(description="List all files in a project.")
    async def list_files_in_project(
        client: ApiClientDep,
        project_id: Annotated[str, Field(description="Project ID.")],
    ) -> Any:
        res = await client.get(f"/graph/projects/{project_id}/files")
        return res.result()

    @mcp.tool(
        description=(
            "FILE OUTLINE & AST STRUCTURE: Retrieve the complete structural outline of a specific code file "
            "(all classes, methods, and functions with their signatures, line ranges, docstrings, and summaries). "
            "Use this tool when you ALREADY KNOW the file path or file name (e.g. 'utils.py' or 'app/utils.py') "
            "and want to inspect what symbols and classes are defined inside it without downloading raw source code. "
            "DO NOT call get_file_content or read_file to re-read the file after this tool, as it already returns "
            "complete signatures and docstrings."
        )
    )
    async def get_file_structure(
        client: ApiClientDep,
        file: Annotated[
            str | None,
            Field(
                default=None,
                description="Target file name or relative path (e.g. 'utils.py', 'backend/app/api/deps.py').",
            ),
        ] = None,
        file_id: Annotated[
            str | None,
            Field(
                default=None,
                description="Direct File ID (UUID) if already known.",
            ),
        ] = None,
        repository_id: Annotated[
            int | None,
            Field(
                default=None,
                description="Repository ID to narrow search scope (recommended).",
            ),
        ] = None,
        workspace_id: Annotated[
            int | None,
            Field(
                default=None,
                description="Workspace ID if known.",
            ),
        ] = None,
    ) -> Any:
        target = file or file_id
        if not target:
            raise ValueError("Either 'file' or 'file_id' must be provided.")

        params: dict[str, Any] = {"file": target}
        if repository_id is not None:
            params["repository_id"] = repository_id
        if workspace_id is not None:
            params["workspace_id"] = workspace_id

        res = await client.get("/graph/files/structure", params=params)
        return res.result()

    @mcp.tool(
        description=(
            "READ RAW SOURCE CODE: Read the full source code (or a specific line range) of a file. "
            "Use this tool ONLY when you need to inspect raw code implementation logic or exact body contents "
            "after you already know the target file path (via get_file_structure or search_in_repo_and_branch). "
            "Do NOT download files repeatedly across the codebase to manually grep for references."
        )
    )
    async def get_file_content(
        client: ApiClientDep,
        file: Annotated[
            str | None,
            Field(default=None, description="File name or relative path (e.g. 'backend/app/crud.py')."),
        ] = None,
        file_id: Annotated[
            str | None,
            Field(default=None, description="Direct File ID (UUID) if known."),
        ] = None,
        line_start: Annotated[
            int | None,
            Field(default=None, ge=1, description="Optional 1-based start line to read from."),
        ] = None,
        line_end: Annotated[
            int | None,
            Field(default=None, ge=1, description="Optional 1-based end line (inclusive)."),
        ] = None,
        repository_id: Annotated[
            int | None,
            Field(default=None, description="Repository ID to narrow scope."),
        ] = None,
        workspace_id: Annotated[
            int | None,
            Field(default=None, description="Workspace ID if known."),
        ] = None,
    ) -> Any:
        target = file or file_id
        if not target:
            raise ValueError("Either 'file' or 'file_id' must be provided.")

        params: dict[str, Any] = {"file": target}
        if line_start is not None:
            params["line_start"] = line_start
        if line_end is not None:
            params["line_end"] = line_end
        if repository_id is not None:
            params["repository_id"] = repository_id
        if workspace_id is not None:
            params["workspace_id"] = workspace_id

        res = await client.get("/graph/files/content", params=params)
        return res.result()

    @mcp.tool(description="Get node metadata: id, name, file_id, position in file.")
    async def get_node_info(
        client: ApiClientDep,
        node_id: Annotated[str, Field(description="Node ID.")],
    ) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}")
        return res.result()

    @mcp.tool(description="Get node source content.")
    async def get_node_content(
        client: ApiClientDep,
        node_id: Annotated[str, Field(description="Node ID.")],
    ) -> Any:
        res = await client.get(f"/graph/nodes/{node_id}/content")
        return res.result()

    @mcp.tool(
        description=(
            "FIND CALLERS & USAGES: Find all functions, methods, route handlers, and classes across the codebase "
            "that call, reference, or import a specific symbol. Returns rich usage details: caller names, "
            "signatures, file paths, and exact call-site line numbers. "
            "Contains complete caller details; do NOT re-read raw source files to trace these usages."
        )
    )
    async def find_node_usages(
        client: ApiClientDep,
        symbol: Annotated[
            str | None,
            Field(
                default=None,
                description="Symbol name to find callers for (e.g. 'get_current_user', 'get_db', 'authenticate').",
            ),
        ] = None,
        node_id: Annotated[
            str | None,
            Field(default=None, description="Direct Node ID (UUID) if known."),
        ] = None,
        file: Annotated[
            str | None,
            Field(default=None, description="File name or path containing the symbol if known."),
        ] = None,
        repository_id: Annotated[
            int | None,
            Field(default=None, description="Repository ID to scope search."),
        ] = None,
        workspace_id: Annotated[
            int | None,
            Field(default=None, description="Workspace ID if known."),
        ] = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        if node_id:
            params["node_id"] = node_id
        if file:
            params["file"] = file
        if repository_id is not None:
            params["repository_id"] = repository_id
        if workspace_id is not None:
            params["workspace_id"] = workspace_id

        if not symbol and not node_id:
            raise ValueError("Either 'symbol' or 'node_id' must be provided.")

        res = await client.get("/graph/nodes/usages", params=params)
        return res.result()

    @mcp.tool(
        description=(
            "FIND CALLEES & DEPENDENCIES: Find all internal helper functions, CRUD utilities, models, and "
            "security methods that a specific function calls. Returns callee names, signatures, file paths, and "
            "exact call-site line numbers in the caller. "
            "Contains complete dependency details; do NOT re-read raw source files to trace these calls."
        )
    )
    async def find_node_callees(
        client: ApiClientDep,
        symbol: Annotated[
            str | None,
            Field(
                default=None, description="Function/symbol name to inspect (e.g. 'login_access_token', 'authenticate')."
            ),
        ] = None,
        node_id: Annotated[
            str | None,
            Field(default=None, description="Direct Node ID (UUID) if known."),
        ] = None,
        file: Annotated[
            str | None,
            Field(
                default=None,
                description="File path containing the symbol if known (e.g. 'app/api/routes/login.py').",
            ),
        ] = None,
        repository_id: Annotated[
            int | None,
            Field(default=None, description="Repository ID to scope search."),
        ] = None,
        workspace_id: Annotated[
            int | None,
            Field(default=None, description="Workspace ID if known."),
        ] = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        if node_id:
            params["node_id"] = node_id
        if file:
            params["file"] = file
        if repository_id is not None:
            params["repository_id"] = repository_id
        if workspace_id is not None:
            params["workspace_id"] = workspace_id

        if not symbol and not node_id:
            raise ValueError("Either 'symbol' or 'node_id' must be provided.")

        res = await client.get("/graph/nodes/callees", params=params)
        return res.result()

    @mcp.tool(
        description=(
            "CONSOLIDATED IMPACT ANALYSIS (BLAST RADIUS): Answers 'if I change symbol X, what is affected?'. "
            "In ONE single call, returns: (1) target definition and line coordinates, (2) all caller usages across "
            "the codebase with exact file paths and line numbers, (3) all callees it invokes, and (4) list of all "
            "affected files. PREFER this tool over calling find_node_usages and find_node_callees separately. "
            "Do NOT re-read raw source files after calling this tool."
        )
    )
    async def analyze_impact(
        client: ApiClientDep,
        symbol: Annotated[
            str | None,
            Field(default=None, description="Symbol name to analyze (e.g. 'get_current_user', 'get_db', 'Settings')."),
        ] = None,
        file: Annotated[
            str | None,
            Field(default=None, description="File name or path containing the symbol if known."),
        ] = None,
        node_id: Annotated[
            str | None,
            Field(default=None, description="Direct Node ID (UUID) if known."),
        ] = None,
        repository_id: Annotated[
            int | None,
            Field(default=None, description="Repository ID to scope search."),
        ] = None,
        workspace_id: Annotated[
            int | None,
            Field(default=None, description="Workspace ID if known."),
        ] = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        if node_id:
            params["node_id"] = node_id
        if file:
            params["file"] = file
        if repository_id is not None:
            params["repository_id"] = repository_id
        if workspace_id is not None:
            params["workspace_id"] = workspace_id

        if not symbol and not node_id:
            raise ValueError("Either 'symbol' or 'node_id' must be provided.")

        res = await client.get("/graph/nodes/impact", params=params)
        return res.result()

    @mcp.tool(
        description=(
            "FIND UNUSED / DEAD CODE (PROJECT): Identify all functions, methods, and classes across the entire project "
            "that are not called or referenced anywhere."
        )
    )
    async def find_unused_nodes_in_project(
        client: ApiClientDep,
        project_id: Annotated[str, Field(description="Project ID.")],
    ) -> Any:
        res = await client.get(f"/graph/projects/{project_id}/unused-nodes")
        return res.result()

    @mcp.tool(
        description=(
            "FIND UNUSED / DEAD CODE (FILE): Identify top-level functions, methods, or classes in a specific file "
            "that have ZERO incoming call or reference edges anywhere in the codebase (excluding tests). "
            "Answers 'identify any top-level functions in file X that are not called or referenced anywhere'."
        )
    )
    async def find_unused_nodes_in_file(
        client: ApiClientDep,
        file_id: Annotated[str, Field(description="File ID (UUID) obtained from get_file_structure.")],
    ) -> Any:
        res = await client.get(f"/graph/files/{file_id}/unused-nodes")
        return res.result()
