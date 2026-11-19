import json
import subprocess
import time
from pathlib import Path

import yaml


def load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_prompt(question_text: str, condition: dict, repo: dict) -> str:
    """Ghép thêm context ID nếu đang chạy ở chế độ MCP để agent không tốn lượt dò ID."""
    parts = [question_text]
    if condition.get("system_hint"):
        parts.append(f"\n[Instruction: {condition['system_hint']}]")

    if condition.get("use_mcp") and "mcp_context" in repo:
        ctx = repo["mcp_context"]
        parts.append(
            f"\n[MCP Parameters: workspace_id={ctx.get('workspace_id')}, "
            f"project_id='{ctx.get('project_id')}', "
            f"repository_id={ctx.get('repository_id')}, "
            f"branch='{ctx.get('branch')}']"
        )
    return "\n".join(parts)


def parse_agy_output(raw_stdout: str, output_format: str) -> dict:
    """
    Bóc tách response, usage tokens, conversation_id và danh sách tool_calls
    từ output của agy (hỗ trợ cả json và stream-json).
    """
    tool_calls = []
    final_payload = {}

    if output_format == "stream-json":
        for line in raw_stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            ev_type = event.get("type", "")
            # Bắt các event gọi tool (tùy schema CLI có thể là tool_use, tool_call, hoặc message chứa content)
            if ev_type in ("tool_use", "tool_call", "function_call"):
                tool_calls.append(
                    {
                        "name": event.get("name") or event.get("tool_name"),
                        "input": event.get("input") or event.get("arguments"),
                    }
                )
            elif ev_type == "assistant" and isinstance(event.get("message"), dict):
                for block in event["message"].get("content", []):
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls.append(
                            {
                                "name": block.get("name"),
                                "input": block.get("input"),
                            }
                        )
            elif ev_type == "result" or "usage" in event:
                final_payload = event
    else:
        # Trường hợp dùng --output-format json truyền thống
        final_payload = json.loads(raw_stdout.strip())
        # Nếu JSON cuối cùng có trường chứa trace/messages thì trích xuất tool_calls từ đó
        for msg in final_payload.get("messages", []):
            for call in msg.get("tool_calls", []):
                tool_calls.append(call)

    return {
        "conversation_id": final_payload.get("conversation_id"),
        "status": final_payload.get("status", "UNKNOWN"),
        "response": final_payload.get("response") or final_payload.get("result", ""),
        "cli_duration_seconds": final_payload.get("duration_seconds"),
        "num_turns": final_payload.get("num_turns"),
        "usage": final_payload.get("usage", {}),
        "tool_calls": tool_calls,
        "tool_call_count": len(tool_calls),
    }


def execute_question(agy_bin: str, prompt: str, repo_path: str, mcp_config: str, out_fmt: str, timeout: int) -> dict:
    command = [
        agy_bin,
        "-p",
        prompt,
        "--output-format",
        out_fmt,
        "--dangerously-skip-permissions",
    ]
    # Mở comment dòng dưới nếu agy của bạn nhận cờ --mcp-config (kiểm tra bằng `agy --help`)
    # if mcp_config:
    #     command.extend(["--mcp-config", str(Path(mcp_config).resolve())])

    t0 = time.perf_counter()
    try:
        res = subprocess.run(
            command,
            cwd=repo_path,  # Khởi chạy agent ngay tại thư mục gốc của repo
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
            "error": e.stderr,
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

    for condition in cfg["conditions"]:
        cond_name = condition["name"]
        result_file = out_dir / f"{cond_name}.jsonl"
        print(f"\n==================== RUNNING: {cond_name} ====================")

        with open(result_file, "a", encoding="utf-8") as f_out:
            for repo in cfg["repositories"]:
                repo_id = repo["id"]
                repo_path = repo["path"]

                for q in repo["questions"]:
                    q_id = q["q_id"]
                    print(f"[{cond_name}] Repo: {repo_id} | Question: {q_id} ...", end=" ", flush=True)

                    prompt = build_prompt(q["text"], condition, repo)
                    run_result = execute_question(
                        agy_bin=settings["agy_binary"],
                        prompt=prompt,
                        repo_path=repo_path,
                        mcp_config=condition.get("mcp_config_path", ""),
                        out_fmt=settings["output_format"],
                        timeout=settings["timeout_seconds"],
                    )

                    record = {
                        "condition": cond_name,
                        "repo_id": repo_id,
                        "question_id": q_id,
                        "dimension": q.get("dimension"),
                        "question_text": q["text"],
                        "metrics": run_result,
                    }

                    # Ghi từng dòng JSONL ngay lập tức
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush()

                    tokens = run_result.get("usage", {}).get("total_tokens", "N/A")
                    calls = run_result.get("tool_call_count", "N/A")
                    print(f"Done ({run_result.get('status')}) | Tokens: {tokens} | Tools: {calls}")


if __name__ == "__main__":
    main()
