"""FastMCP server initialization and tool registration."""

from fastmcp import FastMCP

from .tools.projects import (
    get_active_project,
    list_projects,
    select_project,
    setup_mcp_config,
)

mcp = FastMCP("source-context")


@mcp.tool()
def test_connection(user_name: str) -> str:
    """Sử dụng tool này để kiểm tra xem MCP server có đang hoạt động hay không.

    Args:
        user_name (str): Tên người dùng.

    Returns:
        str: Thông báo xác nhận kết nối thành công.
    """
    return (
        f"Hệ thống báo cáo: Kết nối MCP thành công! Xin chào {user_name}, server source-context-mcp đang chạy hoàn hảo."
    )


mcp.tool()(list_projects)
mcp.tool()(select_project)
mcp.tool()(get_active_project)
mcp.tool()(setup_mcp_config)
