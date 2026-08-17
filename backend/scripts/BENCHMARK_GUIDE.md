# 📘 Hướng Dẫn Đo Đạc & Evaluative Benchmark Cho Dự Án FastAPI Template

Tài liệu này hướng dẫn chi tiết cách chạy thử nghiệm so sánh hiệu năng giữa **Baseline Agent** (Coding Agent thông thường) và **Proposed Agent** (Coding Agent sử dụng hệ thống **Source Context MCP**) trên các repo kiến trúc **FastAPI Template** thông qua **Antigravity Agent CLI** và tệp cấu hình JSON.

---

## 1. Các Chỉ Số Đo Đạc Chi Tiết Thu Thập Được

Hệ thống script tự động trích xuất các chỉ số sau và in ra báo cáo **`BENCHMARK_REPORT.md`**:

1. **Tokens (Prompt Tokens & Completion Tokens):** Đo lường mức độ tiết kiệm dung lượng bộ nhớ context window.
2. **Số lượng Tool Calls (Lần):** Đếm tổng số lần Agent phải gọi công cụ để trả lời câu hỏi.
3. **Chi tiết danh sách tên Tool Call (Tool Execution Sequence):** Hiển thị chính xác **chuỗi các tên tool** được Agent gọi theo thứ tự (Ví dụ: `get_file_structure` $\rightarrow$ `find_node_usages`).
4. **Execution Latency (Giây):** Thời gian thực thi phiên làm việc.

---

## 2. Cấu Trúc Cấu Hình Auto-Approve Trong JSON MCP (`mcp_config_proposed.json`)

Để đảm bảo Agent thực thi các tool của `source-context-mcp` **tự động 100% (không xuất hiện popup hỏi permission)**, tệp cấu hình [mcp_config_proposed.json](file:///c:/Hieu/TTTN/source-context/backend/scripts/mcp_config_proposed.json) đã được bổ sung hai trường `"autoApprove"` và `"alwaysAllow"` cho toàn bộ danh sách MCP Tools.

---

## 3. Các Bước Thực Hiện Đo Đạc

### Bước 1: Clone Repo FastAPI Template muốn test
```bash
cd workspace-repositories
git clone https://github.com/fastapi/full-stack-fastapi-template
```

### Bước 2: Chạy Script Benchmark Tự Động
Mở Terminal tại thư mục gốc của dự án (`c:\Hieu\TTTN\source-context`) và chạy lệnh:

```bash
uv run python backend/scripts/run_agent_benchmark.py
```

### Bước 3: Xem Bảng Báo Cáo Tự Động & Danh Sách Tên Tool
Sau khi kết thúc phiên chạy, hệ thống tự động lưu file **`backend/scripts/BENCHMARK_REPORT.md`** với định dạng báo cáo chuẩn:

#### Mẫu Bảng Tổng Quan:
| Test ID | Tác Vụ Benchmark (FastAPI Template) | Tokens (Baseline vs MCP) | Tiết Kiệm Token (%) | Tool Calls (Base vs MCP) | Latency (s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T01** | Impact Analysis (get_db / Settings) | 18,500 vs 2,100 | **-88.6%** | 9 vs 2 | 19.2s vs 5.3s |
| **T02** | Structure Exploration (App Outline) | 14,200 vs 1,550 | **-89.1%** | 5 vs 1 | 12.1s vs 3.4s |
| **T03** | Dependency Trace (Router to DB) | 52,000 vs 7,200 | **-86.2%** | 14 vs 3 | 26.5s vs 8.1s |

#### Mẫu Chi Tiết Chuỗi Tên Tool Call:
```markdown
#### T01 - Phân tích ảnh hưởng của Core Dependency (get_db / Settings)
- Baseline Agent Tools (9 lượt): `grep_search` → `view_file` → `view_file` → `grep_search` → `view_file` → `view_file` → `view_file` → `grep_search` → `view_file`
- Proposed MCP Agent Tools (2 lượt): `get_file_structure` → `find_node_usages`
```
