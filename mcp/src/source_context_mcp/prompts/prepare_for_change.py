from typing import Annotated

from mcp.server import MCPServer
from pydantic import Field


def register_prompts(mcp: MCPServer):
    @mcp.prompt(
        description="Use when refactor code. Look for object(function, class, ...) usage to detect refactor effect"
    )
    def prepare_for_change(
        target: Annotated[
            str, Field(description="Name of the function, class, method, or variable you are about to change.")
        ],
        project: Annotated[str, Field(description="Project name where the target is located, if known.")] = "",
        change_description: Annotated[
            str, Field(description="Optional description of the change you intend to make.")
        ] = "",
    ):
        change_note = f"\nIntended change: {change_description}\n" if change_description else ""
        project_note = f" in project '{project}'" if project else ""

        return f"""
Prepare for a change to '{target}'{project_note}.{change_note}

Step 1: Locate the Target:
 - If the exact project, file, or node is unclear, use `list_projects`, `list_repositories`, `list_branches`, or \
 semantic search (`search_in_workspace` / `search_in_repo_and_branch`) to find it.
 - Once the project is known, prefer `list_files_in_project` and `get_file_structure` to locate the node without \
 reading full file contents.
 - Use `get_node_info` to confirm you have the right node before proceeding.

Step 2: Understand the Current Implementation:
 - Call `get_node_content` on the target node to review its current signature and behavior.

Step 3: Assess the Blast Radius:
 - Call `find_node_usages` on the target node to list every node that calls or references it. This is the primary \
 signal for how risky the change is - the more usages, the wider the blast radius.
 - For each usage that could be affected (e.g. call sites depending on a changed signature, return type, or \
 behavior), inspect it with `get_node_content` or `get_file_content` to understand exactly how the target is used.

Step 4: Check Internal Dependencies (if the change affects internal logic):
 - Call `find_node_callees` on the target node to see what it depends on, so you don't break assumptions the \
 target relies on.

Step 5: Summarize:
 - List every affected file/node found in Step 3.
 - Flag usages that are likely to break or need updating given the intended change.
 - Recommend what should be tested or reviewed before making the change."""
