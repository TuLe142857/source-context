import sys
from typing import Optional

import typer


def main(
    input_file: Optional[typer.FileText] = typer.Argument(
        None, help="Đường dẫn đến file text. Nếu không cung cấp, tool sẽ đọc từ Standard Input (stdin)."
    ),
):
    """
    CLI Tool xử lý khối văn bản.
    Nhận input từ file hoặc thông qua stdin (hỗ trợ nhiều dòng).
    """
    # 1. Thu thập Input
    if input_file:
        # Nếu user truyền file argument -> Đọc từ file
        content = input_file.read()
    else:
        # Nếu không có file -> Đọc từ stdin
        # Lệnh sys.stdin.read() sẽ nhận toàn bộ văn bản (nhiều dòng) cho đến khi gặp ký tự EOF
        if sys.stdin.isatty():
            typer.echo("Vui lòng nhập văn bản (Nhấn Ctrl+D trên Linux/Mac hoặc Ctrl+Z trên Windows để kết thúc):")

        content = sys.stdin.read()

    # Kiểm tra input rỗng
    if not content.strip():
        typer.echo("Lỗi: Không nhận được khối văn bản nào.", err=True)
        raise typer.Exit(code=1)

    # 2. Xử lý logic của tool tại đây
    # (Ví dụ: đếm số dòng và in ra nội dung đã nhận)
    lines_count = len(content.splitlines())

    typer.secho("\n=== ĐÃ XỬ LÝ THÀNH CÔNG ===", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"Tổng số dòng: {lines_count}")
    typer.echo(f"Tổng số ký tự: {len(content)}")
    typer.echo("---")
    typer.echo(content)


if __name__ == "__main__":
    # Dùng typer.run() thay vì app = typer.Typer() để tạo CLI 1 command duy nhất
    typer.run(main)
