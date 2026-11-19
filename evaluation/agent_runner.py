import json
import subprocess
import time
from pathlib import Path

import yaml


def load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def set_mcp_state(agy_bin: str, server_name: str, enable: bool) -> None:
    """Bật hoặc tắt MCP server thông qua subcommand `agy mcp`."""
    if not server_name:
        return
    action = "enable" if enable else "disable"
    cmd = [agy_bin, "mcp", action, server_name]
    print(f"[Setup] Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"[Warning] `agy mcp {action} {server_name}` returned {res.returncode}: {res.stderr.strip()}")


def load_existing_records(json_path: Path) -> list[dict]:
    """Đọc danh sách kết quả hiện có từ file JSON (nếu có) để hỗ trợ resume."""
    if not json_path.exists():
        return []
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_records_pretty(json_path: Path, records: list[dict]) -> None:
    """Ghi toàn bộ danh sách kết quả ra file JSON được format đẹp (indent=2)."""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def build_prompt(question_text: str, condition: dict, repo: dict) -> str:
    """Tạo prompt hoàn chỉnh, đính kèm tham số định danh repo khi chạy chế độ MCP."""
    parts = [question_text]
    if condition.get("system_hint"):
        parts.append(f"\n[Instruction: {condition['system_hint']}]")

    if condition.get("use_mcp") and "mcp_context" in repo:
        ctx = repo["mcp_context"]
        repo_path = repo.get("path", "")
        parts.append(
            f"\n[MCP Context: repository_id={ctx.get('repository_id')}, "
            f"branch='{ctx.get('branch')}', "
            f"workspace_id={ctx.get('workspace_id')}, "
            f"repo_path='{repo_path}']"
        )
    return "\n".join(parts)


def parse_agy_output(raw_stdout: str, output_format: str) -> dict:
    """
    Bóc tách chính xác schema `stream-json` của Antigravity CLI (`agy`):
    - Tool calls: event == "step_update", step_type == "tool", state == "DONE"
    - Final result: event == "result" -> result.{conversation_id, status, response, duration_seconds, num_turns, usage}
    """
    tool_calls = []
    final_payload = {}
    available_tools = []

    if output_format == "stream-json":
        for line in raw_stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                packet = json.loads(line)
            except json.JSONDecodeError:
                continue

            ev_type = packet.get("event", "")

            if ev_type == "init" and isinstance(packet.get("init"), dict):
                available_tools = packet["init"].get("tools", [])

            elif ev_type == "step_update" and isinstance(packet.get("step_update"), dict):
                step = packet["step_update"]
                if step.get("step_type") == "tool" and step.get("state") == "DONE":
                    tool_info = step.get("tool_info", {})
                    tool_name = step.get("tool_name") or tool_info.get("name")
                    params = tool_info.get("parameters", {})
                    output_raw = tool_info.get("output", "")

                    mcp_subtool = None
                    if tool_name == "call_mcp_tool" and isinstance(params, dict):
                        mcp_subtool = params.get("tool_name") or params.get("name")

                    tool_calls.append(
                        {
                            "step_index": step.get("step_index"),
                            "tool_name": tool_name,
                            "mcp_tool": mcp_subtool,
                            "duration_seconds": step.get("duration_seconds"),
                            "parameters": params,
                            "output_length_chars": len(str(output_raw)),
                        }
                    )

            elif ev_type == "result" and isinstance(packet.get("result"), dict):
                final_payload = packet["result"]
    else:
        parsed = json.loads(raw_stdout.strip())
        final_payload = parsed.get("result", parsed) if isinstance(parsed, dict) else {}

    mcp_call_count = sum(
        1 for tc in tool_calls if tc["tool_name"] == "call_mcp_tool" or str(tc["tool_name"]).startswith("mcp_")
    )

    return {
        "conversation_id": final_payload.get("conversation_id"),
        "status": final_payload.get("status", "UNKNOWN"),
        "response": final_payload.get("response", ""),
        "cli_duration_seconds": final_payload.get("duration_seconds"),
        "num_turns": final_payload.get("num_turns"),
        "usage": final_payload.get("usage", {}),
        "tool_calls": tool_calls,
        "tool_call_count": len(tool_calls),
        "mcp_tool_call_count": mcp_call_count,
        "has_mcp_in_init": "call_mcp_tool" in available_tools,
    }


def execute_question(
    agy_bin: str,
    model: str,
    prompt: str,
    working_dir: str,
    out_fmt: str,
    timeout: int,
) -> dict:
    command = [
        agy_bin,
        "-p",
        prompt,
        "--output-format",
        out_fmt,
        "--dangerously-skip-permissions",
    ]
    if model:
        command.extend(["--model", model])

    t0 = time.perf_counter()
    try:
        res = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        wall_time = round(time.perf_counter() - t0, 3)
        parsed = parse_agy_output(res.stdout, out_fmt)
        parsed["wall_clock_seconds"] = wall_time
        return parsed

    except subprocess.CalledProcessError as e:
        return {
            "status": "ERROR",
            "returncode": e.returncode,
            "error": e.stderr.strip(),
            "stdout_preview": e.stdout[:500] if e.stdout else "",
            "wall_clock_seconds": round(time.perf_counter() - t0, 3),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "wall_clock_seconds": timeout,
        }


def main():
    cfg = load_yaml("benchmark_config.yaml")
    settings = cfg["settings"]
    out_dir = Path(settings["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    empty_dir = Path("/tmp/agy_empty_workspace")
    empty_dir.mkdir(parents=True, exist_ok=True)

    target_agents_dir = empty_dir / ".agents"
    target_agents_dir.mkdir(parents=True, exist_ok=True)
    src_mcp = Path(".agents/mcp_config.json")
    if src_mcp.exists():
        (target_agents_dir / "mcp_config.json").write_text(src_mcp.read_text(encoding="utf-8"), encoding="utf-8")

    agy_bin = settings.get("agy_binary", "agy")
    model = settings.get("model", "")
    mcp_server_name = settings.get("mcp_server_name", "")
    out_fmt = settings.get("output_format", "stream-json")
    timeout = settings.get("timeout_seconds", 300)

    for condition in cfg["conditions"]:
        cond_name = condition["name"]
        if cond_name == "antigravity_default":

            print("ko chay default nua")
            continue
        use_mcp = bool(condition.get("use_mcp", False))
        # Xuất ra file .json thay vì .jsonl để dễ đọc trực tiếp
        result_file = out_dir / f"{cond_name}.json"

        print("\n============================================================")
        print(f"CONDITION: {cond_name} (use_mcp={use_mcp}, model={model})")
        print("============================================================")

        set_mcp_state(agy_bin, mcp_server_name, enable=use_mcp)

        records = load_existing_records(result_file)
        completed_keys = {
            (r["repo_id"], r["question_id"]) for r in records if r.get("metrics", {}).get("status") == "SUCCESS"
        }
        if completed_keys:
            print(f"[Resume] Đã tìm thấy {len(completed_keys)} câu hỏi hoàn tất trước đó, sẽ bỏ qua.")

        for repo in cfg["repositories"]:
            repo_id = repo["id"]
            working_dir = str(empty_dir) if use_mcp else repo["path"]

            if not Path(working_dir).exists():
                print(f"[Skip Repo] Thư mục không tồn tại: {working_dir}")
                continue

            for q in repo["questions"]:
                q_id = q["q_id"]
                if (repo_id, q_id) in completed_keys:
                    print(f"[Skip] {repo_id} -> {q_id} (đã hoàn thành)")
                    continue

                print(f"[{cond_name}] {repo_id} | {q_id} ...", end=" ", flush=True)
                prompt = build_prompt(q["text"], condition, repo)

                run_result = execute_question(
                    agy_bin=agy_bin,
                    model=model,
                    prompt=prompt,
                    working_dir=working_dir,
                    out_fmt=out_fmt,
                    timeout=timeout,
                )

                record = {
                    "condition": cond_name,
                    "model": model,
                    "repo_id": repo_id,
                    "question_id": q_id,
                    "dimension": q.get("dimension"),
                    "question_text": q["text"],
                    "metrics": run_result,
                }

                # Cập nhật bản ghi nếu đã tồn tại bản lỗi trước đó, ngược lại thêm mới
                records = [r for r in records if not (r["repo_id"] == repo_id and r["question_id"] == q_id)]
                records.append(record)
                save_records_pretty(result_file, records)

                status = run_result.get("status")
                tokens = run_result.get("usage", {}).get("total_tokens", "N/A")
                calls = run_result.get("tool_call_count", "N/A")
                mcp_calls = run_result.get("mcp_tool_call_count", 0)
                wall = run_result.get("wall_clock_seconds", "N/A")
                print(f"{status} | Time: {wall}s | Tokens: {tokens} | Tools: {calls} (MCP: {mcp_calls})")

    set_mcp_state(agy_bin, mcp_server_name, enable=True)
    print("\nHoàn tất toàn bộ quá trình benchmark! Kết quả được lưu tại:", out_dir.resolve())


if __name__ == "__main__":
    main()
