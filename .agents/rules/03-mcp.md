---
trigger: always_on
---

# Hướng Dẫn & Quy Tắc Sử Dụng MCP Server `source-context-mcp`

## 1. Phạm Vi Áp Dụng
- Ưu tiên sử dụng MCP Server **`source-context-mcp`** khi tìm hiểu, khám phá, tra cứu cấu trúc, hoặc phân tích tác động thay đổi mã nguồn trong các repository đã được lập chỉ mục (indexed).

## 2. Nguyên Tắc Cốt Lõi: Ưu Tiên Truy Vấn Trực Tiếp (Direct & One-shot First)
- **Truy vấn trực tiếp bằng tên:** Các tool chính (`get_file_structure`, `get_file_content`, `analyze_impact`, `find_node_usages`, `find_node_callees`) đều hỗ trợ truyền trực tiếp tên file/đường dẫn (`file="utils.py"` hoặc `file="app/api/deps.py"`) hoặc tên biểu tượng (`symbol="get_db"`).
- **Không tra cứu ID trung gian lãng phí:** Không cần gọi các tool liệt kê (`list_files_in_project`, `list_projects`,...) chỉ để tìm `file_id` hoặc `node_id` khi bạn đã biết tên file hoặc tên hàm/lớp.
- **Tận dụng dữ liệu giàu thông tin:** Kết quả trả về từ `get_file_structure` và `analyze_impact` đã tích hợp sẵn chữ ký (`signature`), tóm tắt chức năng (`summary`), tọa độ dòng (`start_row`, `end_row`), và docstring. **Tuyệt đối không** gọi lặp `get_node_info` hay `get_node_content` cho từng node chỉ để đọc chữ ký hoặc tóm tắt.

## 3. Bản Đồ Công Cụ Trọng Tâm Theo Mục Đích

| Mục đích | Tool tối ưu | Tham số chính | Đặc điểm |
| :--- | :--- | :--- | :--- |
| **Tìm kiếm ngữ nghĩa kèm Code (Semantic Code Search)**| `search_code_snippets` *(hoặc `search_in_repo_and_branch`)* | `query="<concept_or_feature>"`, `repository_id=...` | **Ưu tiên số 1 khi cần đọc hiểu logic, giải thích thuật toán/validation.** Trả về trực tiếp `code_snippet` triển khai; trả lời ngay trong 1 turn, không gọi lại `get_node_content`. |
| **Tìm kiếm vị trí/Metadata nhanh (Fast Symbol Lookup)**| `search_symbols_metadata` | `query="<symbol_or_concept>"`, `repository_id=...` | **Trinh sát siêu nhẹ:** Trả về `node_id`, `name`, `file_path` để làm đầu vào cho `analyze_impact` hoặc `find_node_usages` mà không tải code. |
| **Phân tích tác động / Blast Radius** | `analyze_impact` | `symbol="<name>"`, `file="<optional>"` | **1 lần gọi duy nhất:** Trả về định nghĩa gốc, toàn bộ callers (kèm số dòng gọi), callees và danh sách file bị ảnh hưởng. |
| **Khám phá cấu trúc file & Outline** | `get_file_structure` | `file="<path_or_name>"` | Trả về cây AST phong phú của file (classes, methods, signatures, summaries, line ranges) khi đã biết tên/đường dẫn file. |
| **Tìm các nơi gọi (Callers / Usages)** | `find_node_usages` | `symbol="<name>"`, `file="<optional>"` | Danh sách chi tiết các hàm/lớp gọi tới symbol kèm signature và dòng gọi. |
| **Tìm các hàm phụ thuộc (Callees)** | `find_node_callees` | `symbol="<name>"`, `file="<optional>"` | Danh sách các hàm mà symbol này gọi tới. |
| **Đọc mã nguồn chi tiết** | `get_file_content` | `file="<path_or_name>"` | Đọc nội dung file khi cần xem chi tiết logic triển khai. |

## 4. Quy Trình Khám Phá Dự Án Mới (Khi Chưa Biết Context)
Chỉ thực hiện khi bắt đầu khám phá một dự án mới hoàn toàn chưa rõ cấu trúc:
1. **Xác định Repository:** Nếu chưa có `repository_id`, gọi `list_workspaces` $\rightarrow$ `list_repositories`.
2. **Tổng quan kiến trúc một chạm:** Gọi ngay `get_repository_overview(repository_id)` để nắm toàn bộ tech stack, framework, entrypoints và directory map trong **1 lần gọi**.
3. **Chuyển ngay sang truy vấn trực tiếp:** Sau khi có bức tranh kiến trúc, dùng ngay `get_file_structure` hoặc `search_in_repo_and_branch` cho các file/chức năng cần tìm hiểu. Không gọi lại các tool listing.

## 5. Quy Tắc Tiết Kiệm Token & Tin Tưởng Đồ Thị (Anti-Paranoia)
- **Tin tưởng kết quả phân tích Graph & AST:** Khi các tool đồ thị (`analyze_impact`, `find_node_usages`, `find_node_callees`, `get_file_structure`) trả về kết quả, hãy sử dụng trực tiếp kết quả đó để trả lời.
- **Tin tưởng kết quả Semantic Search kèm Code Snippet:** Khi sử dụng `search_code_snippets` (hoặc `search_in_repo_and_branch`), kết quả đã chứa sẵn thân mã nguồn (`code_snippet`). Trả lời ngay lập tức dựa trên snippet này, tuyệt đối không gọi thêm `get_node_content` hay `get_file_content` chỉ để đọc lại đoạn code đó.
- **Nghiêm cấm tải hàng loạt mã nguồn:** Tuyệt đối không gọi `get_file_content` lặp đi lặp lại trên nhiều file chỉ để grep/đọc chéo thủ công khi đồ thị đã phân tích. Chỉ đọc nội dung của đúng 1 file mục tiêu khi câu hỏi yêu cầu xem mã nguồn chi tiết của file hoặc hàm đó.
- **Xử lý quan hệ gián tiếp / Alias:** Nếu một hàm được bọc qua dependency alias (ví dụ: `CurrentUser = Annotated[..., Depends(get_current_user)]`), hãy truy vấn usages của alias (`symbol="CurrentUser"`) hoặc kiểm tra chữ ký ở file khai báo, không tải thủ công toàn bộ các file trong dự án.
