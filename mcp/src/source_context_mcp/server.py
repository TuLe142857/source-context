from fastmcp import FastMCP

mcp = FastMCP("source-context")


@mcp.tool()
def test_connection(user_name: str) -> str:
    """
    Sử dụng tool này để kiểm tra xem MCP server có đang hoạt động hay không.
    Trả về một thông báo xác nhận kết nối thành công.
    """
    return (
        f"Hệ thống báo cáo: Kết nối MCP thành công! "
        f"Xin chào {user_name}, server source-context-mcp đang chạy hoàn hảo."
    )
