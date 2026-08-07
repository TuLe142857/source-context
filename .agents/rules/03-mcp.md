---
trigger: always_on
---

# Hướng Dẫn & Quy Tắc Sử Dụng MCP Server `source-context-mcp`

## 1. Phạm Vi Áp Dụng
- Bắt buộc ưu tiên sử dụng MCP Tool **`source-context-mcp`** khi được yêu cầu tìm hiểu, khám phá hoặc phân tích các dự án/repository bên ngoài (không thuộc codebase hiện tại).

## 2. Quy Trình Khám Phá Theo Cấp Độ (Discovery Workflow)
Thực hiện tra cứu theo thứ tự từ tổng quan đến chi tiết:
1. **Workspace:** Dùng `list_workspaces` để xác định các không gian làm việc khả dụng.
2. **Repository:** Dùng `list_repositories` với `workspace_id` thu được.
3. **Branch & Project:** Dùng `list_branches` và `list_projects` để lấy danh sách nhánh (branch) và project con.
4. **File List:** Dùng `list_files_in_project` để xem danh sách toàn bộ các file trong project.

## 3. Tối Ưu Hóa Token & Hiệu Năng
- **Ưu tiên tổng quan:** Dùng `get_file_structure` hoặc `list_files_in_project` để nắm cấu trúc thư mục trước khi đọc nội dung code.
- **Hạn chế tiêu thụ Token:** Chỉ gọi `get_file_content` đối với các file thực sự quan trọng (file cấu hình, entrypoint, models cốt lõi). Không tải nội dung file tràn lan.
- **Tìm kiếm chính xác:** Dùng `search_in_workspace` hoặc `search_in_repo_and_branch` để tìm kiếm từ khóa/hàm cụ thể thay vì duyệt từng file thủ công.

## 4. Tra Cứu Logic & Dependency, các quan hệ phụ thuộc, gọi giữa các node, file (Phân Tích Code)
- Dùng `find_node_usages` và `find_node_callees` để phân tích luồng gọi hàm và phụ thuộc giữa các module khi cần thiết.
- Dùng `get_node_info` và `get_node_content` để xem chi tiết class/function.

