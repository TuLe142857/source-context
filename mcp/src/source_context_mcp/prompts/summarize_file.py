from typing import Annotated

from mcp.server import MCPServer
from pydantic import Field


def register_prompts(mcp: MCPServer):
    @mcp.prompt(description="Summarize file")
    def summarize_file(
        file: Annotated[str, Field(description="File path or file name to summarize.")],
        project: Annotated[
            str, Field(description="Project name the file belongs to, to help locate it if the path is ambiguous.")
        ] = "",
    ):
        project_note = f" in project '{project}'" if project else ""

        return f"""
Summarize the file '{file}'{project_note}.

Step 1: Locate the File:
 - If the exact project or file ID is unclear, use `list_projects` to find the project, then `list_files_in_project` \
 to find the matching file.

Step 2: Inspect Structure (Token-Efficient Approach):
 - Start with `get_file_structure` to see the file's classes, methods, and functions without reading the full \
 source.
 - Only call `get_file_content` if you need the actual implementation details to write an accurate summary.

Step 3: Summarize:
 - State the file's purpose and its role within the project.
 - List its main classes/functions and what each one does, at a high level.
 - Note any notable dependencies or relationships to other parts of the codebase (use `find_node_usages` or \
 `find_node_callees` on specific nodes only if that context is needed)."""
