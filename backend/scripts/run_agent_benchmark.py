"""Benchmark evaluation script for Antigravity AGY CLI Agent on FastAPI Template Codebases.

Single Scenario Benchmark (T01 Impact Analysis).
Compares Baseline Agent (Strict Filesystem Tools) vs Proposed Agent (Strict Source Context MCP Tools).
Exports token usage, latency, tool calls sequence, and full agent response outputs.

Usage:
    uv run python backend/scripts/run_agent_benchmark.py
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure Windows stdout/stderr supports UTF-8 Vietnamese encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Workspace Root & Locked Target Cloned Repository Setup
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

possible_repos = [
    WORKSPACE_ROOT / "workspace-repositories" / "full-stack-fastapi-template",
    WORKSPACE_ROOT / "workspace-repositories" / "fastapi-template",
]

DEFAULT_TARGET_REPO = possible_repos[0]
for repo in possible_repos:
    if repo.exists():
        DEFAULT_TARGET_REPO = repo
        break

TARGET_REPO_PATH = DEFAULT_TARGET_REPO

# Locked MCP Context Defaults
LOCKED_WORKSPACE_ID = 1
LOCKED_REPOSITORY_ID = 1
LOCKED_BRANCH_NAME = "master"


class BenchmarkMetrics:
    """Data class holding benchmark evaluation metrics for a single test run."""

    def __init__(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        tool_calls: int = 0,
        tool_names: list[str] | None = None,
        latency_sec: float = 0.0,
        output_text: str = "",
    ) -> None:
        """Initializes benchmark metrics.

        Args:
            prompt_tokens (int): Total input prompt tokens.
            completion_tokens (int): Total output completion tokens.
            tool_calls (int): Number of tool execution calls.
            tool_names (list[str] | None): Ordered list of invoked tool names.
            latency_sec (float): Total execution duration in seconds.
            output_text (str): Final text answer output.
        """
        self.prompt_tokens: int = prompt_tokens
        self.completion_tokens: int = completion_tokens
        self.total_tokens: int = prompt_tokens + completion_tokens
        self.tool_calls: int = tool_calls
        self.tool_names: list[str] = tool_names or []
        self.latency_sec: float = latency_sec
        self.output_text: str = output_text


# -----------------------------------------------------------------------------
# BENCHMARK SUITE CONFIGURATION (SINGLE SCENARIO T01 ONLY)
# -----------------------------------------------------------------------------
BENCHMARK_TESTS: list[dict[str, str]] = [
    {
        "id": "T01",
        "category": "Impact Analysis",
        "name": "Phân tích ảnh hưởng của Core Dependency (get_db / Settings)",
        "prompt": (
            "Trong dự án FastAPI này, hãy tìm nơi định nghĩa class/phương thức 'get_db' "
            "(hoặc 'Settings' / 'get_current_user') và liệt kê chính xác tất cả các API router hoặc "
            "module đang import và sử dụng nó."
        ),
    },
]


def ensure_git_master_branch(repo_dir: Path) -> None:
    """Ensures target git repository is checked out on the master branch.

    Args:
        repo_dir (Path): Path to the target git repository.
    """
    if not (repo_dir / ".git").exists():
        return

    try:
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"[GIT] Checked out branch '{LOCKED_BRANCH_NAME}' in {repo_dir.name}")
    except subprocess.SubprocessError as err:
        print(f"[WARNING] Could not checkout master branch: {err}")


def find_agy_binary() -> str:
    """Finds the installed `agy` CLI binary on system PATH or default user location.

    Returns:
        str: Resolving binary command or path.
    """
    for name in ["agy", "agy.exe", "agy.cmd"]:
        found = shutil.which(name)
        if found:
            return found

    user_home = Path(os.path.expanduser("~"))
    fallback_path = user_home / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
    if fallback_path.exists():
        return str(fallback_path)

    return "agy"


def setup_target_mcp_config(target_dir: Path, source_config_path: Path | None) -> None:
    """Sets up or clears .agents/mcp_config.json inside target_dir for session execution.

    Args:
        target_dir (Path): Working directory.
        source_config_path (Path | None): Config file to copy or None to clear.
    """
    agents_dir = target_dir / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    target_config = agents_dir / "mcp_config.json"

    if source_config_path and source_config_path.exists():
        shutil.copy2(source_config_path, target_config)
    else:
        with open(target_config, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {}}, f, indent=2)


def run_single_agy_stream_session(
    prompt: str,
    target_dir: Path,
    config_path: Path | None = None,
    is_baseline: bool = False,
) -> BenchmarkMetrics:
    """Executes a single agy CLI session in stream-json mode, parsing real-time events.

    Args:
        prompt (str): Input prompt query.
        target_dir (Path): Working repository directory.
        config_path (Path | None): Path to MCP config JSON file if present.
        is_baseline (bool): Flag indicating baseline mode.

    Returns:
        BenchmarkMetrics: Real execution metrics captured from stream-json events.
    """
    start_time = time.time()
    exec_dir = target_dir if target_dir.exists() else WORKSPACE_ROOT
    agy_bin = find_agy_binary()

    # Set up local .agents/mcp_config.json inside working directory
    setup_target_mcp_config(exec_dir, config_path if not is_baseline else None)

    # Build prompt with strict tool instructions
    if is_baseline:
        active_prompt = (
            f"{prompt} (Nghiêm cấm: KHÔNG sử dụng MCP tools hoặc call_mcp_tool. "
            "CHỈ sử dụng các công cụ đọc file thô thông thường như grep_search, view_file, list_dir)."
        )
        agent_type = "BASELINE AGENT (NO MCP)"
    else:
        active_prompt = (
            f"{prompt} (Nghiêm cấm: Sử dụng bộ công cụ Source Context MCP qua call_mcp_tool với "
            f"workspace_id={LOCKED_WORKSPACE_ID}, repository_id={LOCKED_REPOSITORY_ID}, branch='{LOCKED_BRANCH_NAME}' "
            "để tra cứu trực tiếp theo cây cú pháp AST thay vì đọc thủ công từng file thô)."
        )
        agent_type = "PROPOSED AGENT (WITH MCP)"

    print(f"\n   [{agent_type}] Running in: '{exec_dir.name}'")
    print(f"   📝 Prompt: '{active_prompt[:80]}...'")

    cmd: list[str] = [
        agy_bin,
        "--output-format",
        "stream-json",
        "--dangerously-skip-permissions",
        "-p",
        active_prompt,
    ]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(exec_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except FileNotFoundError:
        print(f"❌ Error: Could not execute command '{agy_bin}'")
        return BenchmarkMetrics()

    tool_names_list: list[str] = []
    final_usage: dict[str, Any] = {}
    full_text = ""

    if process.stdout:
        for line in process.stdout:
            line_str = line.strip()
            if not line_str:
                continue

            try:
                data = json.loads(line_str)
                event = data.get("event")

                if event == "step_update":
                    step = data.get("step_update", {})
                    step_type = step.get("step_type")

                    # Parse tool calls
                    if step_type == "tool":
                        tool_name = (
                            step.get("name")
                            or step.get("tool_name")
                            or step.get("tool_call", {}).get("name")
                            or "Unknown_Tool"
                        )
                        tool_names_list.append(tool_name)
                        print(f"      [🛠️ TOOL CALL] -> {tool_name}")

                    # Capture text output
                    elif "text_delta" in step and step["text_delta"]:
                        full_text += step["text_delta"]

                    # Capture token usage
                    if "usage" in step and isinstance(step["usage"], dict):
                        final_usage.update(step["usage"])

                elif event == "result":
                    res = data.get("result", {})
                    if "usage" in res and isinstance(res["usage"], dict):
                        final_usage.update(res["usage"])

            except json.JSONDecodeError:
                pass

    process.wait()
    latency = round(time.time() - start_time, 2)

    prompt_tokens = int(
        final_usage.get("input_tokens", 0) or final_usage.get("prompt_tokens", 0)
    )
    completion_tokens = int(
        final_usage.get("output_tokens", 0) or final_usage.get("completion_tokens", 0)
    )

    return BenchmarkMetrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        tool_calls=len(tool_names_list),
        tool_names=tool_names_list,
        latency_sec=latency,
        output_text=full_text,
    )


def generate_benchmark_markdown_report(
    results: list[dict[str, Any]],
    repo_path: Path,
) -> str:
    """Generates a GitHub-flavored Markdown report comparing Baseline vs Proposed MCP metrics.

    Args:
        results (list[dict[str, Any]]): List of test result dictionaries.
        repo_path (Path): Path to the benchmarked target repository.

    Returns:
        str: Formatted Markdown table, tool list summary, and full agent text outputs.
    """
    lines: list[str] = [
        "# 📊 Báo Cáo Kết Quả Benchmark Coding Agent (T01 Impact Analysis)",
        "",
        f"**Thời gian đo:** `{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}`",
        f"**Thư mục Repo Thử Nghiệm (Cố định):** `{repo_path}` (Branch: `{LOCKED_BRANCH_NAME}`)",
        f"**Cấu hình MCP Cố định:** Workspace ID = `{LOCKED_WORKSPACE_ID}`, Repository ID = `{LOCKED_REPOSITORY_ID}`",
        "",
        "Đánh giá hiệu năng giữa **Baseline Agent** (Tool đọc file thô) và **Proposed Agent** (Source Context MCP).",
        "",
        "| Test ID | Tác Vụ Benchmark | Tokens (Baseline vs MCP) | Tiết Kiệm Token (%) | Tool Calls (Base vs MCP) | Latency (s) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    total_base_tokens = 0
    total_mcp_tokens = 0

    for r in results:
        base_tok: int = r["baseline"].total_tokens
        mcp_tok: int = r["proposed"].total_tokens
        total_base_tokens += base_tok
        total_mcp_tokens += mcp_tok

        saving = round((1 - mcp_tok / base_tok) * 100, 1) if base_tok > 0 else 0.0

        tok_str = f"{base_tok:,} vs {mcp_tok:,}"
        tool_str = f"{r['baseline'].tool_calls} vs {r['proposed'].tool_calls}"
        time_str = f"{r['baseline'].latency_sec}s vs {r['proposed'].latency_sec}s"

        lines.append(
            f"| **{r['id']}** | {r['name']} | {tok_str} | **-{saving}%** | {tool_str} | {time_str} |"
        )

    avg_saving = (
        round((1 - total_mcp_tokens / total_base_tokens) * 100, 1)
        if total_base_tokens > 0
        else 0.0
    )

    lines.extend(
        [
            "",
            "### 📈 Tóm Tắt Tổng Quan",
            f"- **Tổng Token Tiêu Tốn (Baseline):** {total_base_tokens:,} tokens",
            f"- **Tổng Token Tiêu Tốn (Proposed MCP):** {total_mcp_tokens:,} tokens",
            f"- **Mức độ Tiết kiệm Token:** **-{avg_saving}%**",
            "",
            "---",
            "",
            "### 🛠️ Chi Tiết Danh Sách Tên Tool Call Thực Tế",
            "",
        ]
    )

    for r in results:
        base_tools_fmt = (
            " → ".join([f"`{t}`" for t in r["baseline"].tool_names])
            if r["baseline"].tool_names
            else "Không gọi tool"
        )
        mcp_tools_fmt = (
            " → ".join([f"`{t}`" for t in r["proposed"].tool_names])
            if r["proposed"].tool_names
            else "Không gọi tool"
        )

        lines.extend(
            [
                f"#### **{r['id']} - {r['name']}**",
                f"- **Baseline Agent Tools ({r['baseline'].tool_calls} lượt):**",
                f"  {base_tools_fmt}",
                f"- **Proposed MCP Agent Tools ({r['proposed'].tool_calls} lượt):**",
                f"  {mcp_tools_fmt}",
                "",
                "---",
                "",
                "### 💬 Nội Dung Phản Hồi (Output Kết Quả Của Agent)",
                "",
                "#### 1. Baseline Agent Output:",
                f"```text\n{r['baseline'].output_text.strip() or '(Không có nội dung trả về)'}\n```",
                "",
                "#### 2. Proposed MCP Agent Output:",
                f"```text\n{r['proposed'].output_text.strip() or '(Không có nội dung trả về)'}\n```",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    """Main function executing the AGY Agent Benchmark suite for single T01 scenario."""
    print("=" * 75)
    print("  ANTIGRAVITY BENCHMARK SUITE - TEST CASE T01 (IMPACT ANALYSIS ONLY)")
    print("=" * 75)

    # Ensure target repository is on master branch
    ensure_git_master_branch(TARGET_REPO_PATH)

    script_dir = Path(__file__).resolve().parent
    baseline_config = script_dir / "mcp_config_baseline.json"
    proposed_config = script_dir / "mcp_config_proposed.json"

    print(f"[TARGET REPO] Path: '{TARGET_REPO_PATH}' | Branch: '{LOCKED_BRANCH_NAME}'")
    print(
        f"[LOCKED MCP DEFAULTS] Workspace ID: {LOCKED_WORKSPACE_ID} | Repository ID: {LOCKED_REPOSITORY_ID}"
    )

    results: list[dict[str, Any]] = []

    print("\n[1/1] Running T01 Benchmark Test (Baseline vs Proposed MCP)...")
    print("-" * 75)

    for test in BENCHMARK_TESTS:
        print(f"\n>>> Running Test Scenario [{test['id']}]: {test['name']}")

        # 1. Run Baseline Agent Session
        metrics_base = run_single_agy_stream_session(
            prompt=test["prompt"],
            target_dir=TARGET_REPO_PATH,
            config_path=baseline_config if baseline_config.exists() else None,
            is_baseline=True,
        )

        # 2. Run Proposed MCP Agent Session
        metrics_mcp = run_single_agy_stream_session(
            prompt=test["prompt"],
            target_dir=TARGET_REPO_PATH,
            config_path=proposed_config if proposed_config.exists() else None,
            is_baseline=False,
        )

        results.append(
            {
                "id": test["id"],
                "name": test["name"],
                "category": test["category"],
                "baseline": metrics_base,
                "proposed": metrics_mcp,
            }
        )

        # Save individual output files for reference
        try:
            with open(
                script_dir / "BASELINE_ANSWER_T01.md", "w", encoding="utf-8"
            ) as f:
                f.write(metrics_base.output_text)
            with open(
                script_dir / "PROPOSED_MCP_ANSWER_T01.md", "w", encoding="utf-8"
            ) as f:
                f.write(metrics_mcp.output_text)
        except OSError as err:
            print(f"[WARNING] Could not save separate answer files: {err}")

    # Save and output Markdown report
    report_md = generate_benchmark_markdown_report(results, TARGET_REPO_PATH)
    report_path = script_dir / "BENCHMARK_REPORT.md"

    try:
        with open(report_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(report_md)
        print(f"\n[SUCCESS] Saved benchmark report to {report_path}")
    except OSError as err:
        print(f"[ERROR] Failed to save report: {err}")

    print("\n" + report_md)


if __name__ == "__main__":
    main()
