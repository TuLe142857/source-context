from typing import Annotated

from mcp.server import MCPServer
from pydantic import Field


def register_prompts(mcp: MCPServer):
    @mcp.prompt(
        description="Analyze the software architecture of the given project",
    )
    def analyze_architecture(project: Annotated[str, Field(description="Project name")]):
        return f"""
Analyze the software architecture of the project: '{project}'.

Step 1:Identify the Project:
 - If the exact project location or repository is unclear, use tools such as `list_projects`, `list_repositories`, \
 or `list_branches` to locate and confirm the target project.

Step 2: Analyze Project Structure (Token-Efficient Approach):
 - Start by calling `get_file_structure` (or `list_files`) to inspect the directory layout.
 - *Best Practice*: Always prefer `get_file_structure` first, as it returns only the structure without full source \
 code, conserving API tokens.
 - Only call `get_file_content` for specific files when you need detailed implementation insights.

Step 3: Deepen Architecture Analysis(If needed):
 - Depending on the architecture aspects you are investigating, use additional tools such as `find_node_usages`, \
 `find_node_callees`, or any other relevant analysis tools to trace dependencies and data flow.

Provide a clear, structured summary of the architectural patterns, key components, and relationships found in the \
project."""
