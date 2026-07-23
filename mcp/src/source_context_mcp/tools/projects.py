"""MCP Tools for project selection, list retrieval, and workspace configuration."""

import os

from ..api_client import FastAPIClient, FastAPIClientError
from ..config import (
    get_project_id_for_dir,
    load_config,
    set_api_key,
    set_project_id_for_dir,
)


async def list_projects() -> str:
    """Sử dụng tool này để lấy danh sách các Project mà người dùng có quyền truy cập từ FastAPI backend.

    Returns:
        str: Danh sách project dạng chuỗi định dạng (ID, Tên, Mô tả) hoặc thông báo lỗi.
    """
    client = FastAPIClient()
    try:
        projects = await client.list_projects()
        if not projects:
            return "Không tìm thấy project nào. Bạn chưa sở hữu hoặc tham gia vào project nào trên hệ thống."

        formatted_lines = [f"Danh sách Project khả dụng ({len(projects)} project):"]
        for p in projects:
            p_id = p.get("id")
            p_name = p.get("project_name", "N/A")
            p_desc = p.get("description", "Không có mô tả")
            formatted_lines.append(f"- ID: {p_id} | Tên: {p_name} | Mô tả: {p_desc}")

        formatted_lines.append("\nSử dụng tool 'select_project(project_id=...)' để chọn project làm việc.")
        return "\n".join(formatted_lines)
    except FastAPIClientError as exc:
        return f"Lỗi khi lấy danh sách project từ backend: {exc}"


async def select_project(project_id: int, bind_to_workspace: bool = True) -> str:
    """Sử dụng tool này để chọn một Project theo ID để làm việc.

    Args:
        project_id (int): ID của project muốn chọn.
        bind_to_workspace (bool, optional): Có gán project ID này với thư mục làm việc hiện tại hay không.
            Defaults to True.

    Returns:
        str: Thông báo kết quả chọn project.
    """
    client = FastAPIClient()
    try:
        project_info = await client.get_project(project_id)
        current_dir = os.getcwd()

        if bind_to_workspace:
            set_project_id_for_dir(current_dir, project_id)
            bind_msg = f"Đã gán thành công Project ID {project_id} cho thư mục làm việc: '{current_dir}'."
        else:
            config = load_config()
            config.active_project_id = project_id
            bind_msg = f"Đã đặt Project ID {project_id} làm active project mặc định toàn cục."

        p_name = project_info.get("project_name", "N/A")
        return (
            f"{bind_msg}\n"
            f"Thông tin Project đang làm việc:\n"
            f"- ID: {project_id}\n"
            f"- Tên: {p_name}\n"
            f"- Mô tả: {project_info.get('description', 'N/A')}"
        )
    except FastAPIClientError as exc:
        return f"Lỗi khi kiểm tra Project ID {project_id}: {exc}"


async def get_active_project() -> str:
    """Sử dụng tool này để xem thông tin Project hiện đang được chọn cho thư mục làm việc hiện tại.

    Returns:
        str: Thông tin project active hoặc cảnh báo nếu chưa chọn project cho thư mục hiện tại.
    """
    current_dir = os.getcwd()
    project_id = get_project_id_for_dir(current_dir)

    if project_id is None:
        return (
            f"CHƯA CHỌN PROJECT cho thư mục hiện tại: '{current_dir}'.\n"
            f"Vui lòng thực hiện các bước sau:\n"
            f"1. Gọi tool 'list_projects' để xem danh sách project khả dụng.\n"
            f"2. Gọi tool 'select_project(project_id=...)' để chọn project tương ứng."
        )

    client = FastAPIClient()
    try:
        project_info = await client.get_project(project_id)
        p_name = project_info.get("project_name", "N/A")
        return (
            f"Thư mục làm việc hiện tại: '{current_dir}'\n"
            f"Project đang active:\n"
            f"- ID: {project_id}\n"
            f"- Tên: {p_name}\n"
            f"- Mô tả: {project_info.get('description', 'N/A')}"
        )
    except FastAPIClientError as exc:
        return (
            f"Thư mục '{current_dir}' đang được gán với Project ID {project_id}, "
            f"nhưng không thể lấy thông tin từ backend: {exc}"
        )


def setup_mcp_config(api_key: str, server_url: str | None = None) -> str:
    """Sử dụng tool này để cấu hình API Key (Personal Access Token) và URL Backend cho MCP server.

    Args:
        api_key (str): Mã API Key do FastAPI cấp (dạng sc_live_...).
        server_url (str | None, optional): Địa chỉ FastAPI Backend. Defaults to None.

    Returns:
        str: Thông báo kết quả lưu cấu hình.
    """
    set_api_key(api_key, server_url)
    config = load_config()
    key_preview = f"{config.api_key[:10]}... [đã ẩn]" if config.api_key else "Chưa thiết lập"
    return f"Cấu hình MCP Server đã được lưu thành công!\n- Server URL: {config.server_url}\n- API Key: {key_preview}"
