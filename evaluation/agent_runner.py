"""Agent Runner for Source Context Benchmark.

Executes benchmark questions using the Antigravity CLI (`agy`) across multiple
experimental conditions (e.g. antigravity_mcp vs antigravity_default).
Collects detailed tool calls, token usage, execution time, and model responses
into structured JSON result files for downstream judging.
"""

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Loads a YAML configuration file.

    Args:
        path (str | Path): Path to the YAML file.

    Returns:
        dict[str, Any]: Parsed configuration dictionary.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}


def set_mcp_state(agy_bin: str, server_name: str, enable: bool) -> None:
    """Enables or disables an MCP server in the Antigravity CLI via subcommand.

    Args:
        agy_bin (str): Path to or name of the agy binary.
        server_name (str): The MCP server name to configure.
        enable (bool): True to enable, False to disable.
    """
    if not server_name:
        return
    action = "enable" if enable else "disable"
    cmd = [agy_bin, "mcp", action, server_name]
    logger.info("[Setup] Executing: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        logger.warning(
            "`agy mcp %s %s` returned %d: %s",
            action,
            server_name,
            res.returncode,
            res.stderr.strip(),
        )


def load_existing_records(json_path: Path) -> list[dict[str, Any]]:
    """Reads existing benchmark records from JSON to support incremental resume.

    Args:
        json_path (Path): Path to the target JSON result file.

    Returns:
        list[dict[str, Any]]: Existing list of evaluation records.
    """
    if not json_path.exists():
        return []
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_records_pretty(json_path: Path, records: list[dict[str, Any]]) -> None:
    """Saves the complete record list to a formatted JSON file (indent=2).

    Args:
        json_path (Path): Path to output file.
        records (list[dict[str, Any]]): Records to serialize.
    """
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def build_prompt(question_text: str, condition: dict[str, Any], repo: dict[str, Any]) -> str:
    """Constructs the full prompt injected into the Antigravity agent CLI.

    Args:
        question_text (str): Benchmark question text.
        condition (dict[str, Any]): Test condition definition with optional system_hint.
        repo (dict[str, Any]): Target repository metadata with mcp_context.

    Returns:
        str: Fully formatted prompt string.
    """
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


def parse_agy_output(raw_stdout: str, output_format: str) -> dict[str, Any]:
    """Parses stream-json output from Antigravity CLI.

    Args:
        raw_stdout (str): Raw stdout stream from agy.
        output_format (str): Output format specification (e.g. stream-json).

    Returns:
        dict[str, Any]: Aggregated execution metrics and tool calls.
    """
    tool_calls: list[dict[str, Any]] = []
    final_payload: dict[str, Any] = {}
    available_tools: list[str] = []

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
        try:
            parsed = json.loads(raw_stdout.strip())
            final_payload = parsed.get("result", parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            final_payload = {}

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
) -> dict[str, Any]:
    """Executes a single benchmark question via the Antigravity CLI.

    Args:
        agy_bin (str): Path to agy CLI.
        model (str): LLM model name.
        prompt (str): Full prompt text.
        working_dir (str): Execution directory.
        out_fmt (str): Output format.
        timeout (int): Timeout in seconds.

    Returns:
        dict[str, Any]: Parsed execution record with wall clock timing.
    """
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
            "error": e.stderr.strip() if e.stderr else "",
            "stdout_preview": e.stdout[:500] if e.stdout else "",
            "wall_clock_seconds": round(time.perf_counter() - t0, 3),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "wall_clock_seconds": timeout,
        }


def sync_agents_workspace(empty_dir: Path, project_root: Path) -> None:
    """Synchronizes MCP configuration and agent rules into the isolated workspace.

    Args:
        empty_dir (Path): The isolated workspace directory for MCP evaluation.
        project_root (Path): The repository root containing the .agents directory.
    """
    empty_dir.mkdir(parents=True, exist_ok=True)
    target_agents_dir = empty_dir / ".agents"
    target_agents_dir.mkdir(parents=True, exist_ok=True)

    src_agents_dir = project_root / ".agents"
    if not src_agents_dir.exists():
        src_agents_dir = Path(".agents")

    if src_agents_dir.exists():
        # Copy mcp_config.json
        src_mcp = src_agents_dir / "mcp_config.json"
        if src_mcp.exists():
            (target_agents_dir / "mcp_config.json").write_text(src_mcp.read_text(encoding="utf-8"), encoding="utf-8")

        # Copy rules (especially 03-mcp.md)
        src_rules = src_agents_dir / "rules"
        if src_rules.exists():
            target_rules_dir = target_agents_dir / "rules"
            target_rules_dir.mkdir(parents=True, exist_ok=True)
            for rule_file in src_rules.glob("*.md"):
                (target_rules_dir / rule_file.name).write_text(rule_file.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info("Synchronized agent rules from %s to %s", src_rules, target_rules_dir)


def main() -> None:
    """Main CLI entrypoint for orchestrating benchmark agent runs."""
    parser = argparse.ArgumentParser(description="Antigravity Benchmark Agent Runner")
    parser.add_argument(
        "--config",
        type=str,
        default="benchmark_config.yaml",
        help="Path to benchmark_config.yaml",
    )
    parser.add_argument(
        "--condition",
        type=str,
        default=None,
        help="Filter to a specific condition (e.g. antigravity_mcp, antigravity_default)",
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="Filter to a specific question ID (e.g. Q3_core_dependencies, Q4_semantic_search)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run questions even if already completed with SUCCESS status",
    )
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    project_root = eval_dir.parent

    # Resolve config path flexibly
    config_path = Path(args.config)
    if not config_path.exists():
        for candidate in [
            eval_dir / args.config,
            eval_dir / Path(args.config).name,
            project_root / "evaluation" / "benchmark_config.yaml",
            Path("benchmark_config.yaml"),
        ]:
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        logger.error("Config file not found: %s", args.config)
        return

    cfg = load_yaml(config_path)
    settings = cfg.get("settings", {})

    out_dir = Path(settings.get("output_dir", "./eval_results"))
    if not out_dir.is_absolute():
        candidates = [eval_dir / out_dir, eval_dir / out_dir.name, out_dir]
        for c in candidates:
            if c.parent.exists():
                out_dir = c
                break
    out_dir.mkdir(parents=True, exist_ok=True)

    empty_dir = Path("/tmp/agy_empty_workspace")
    sync_agents_workspace(empty_dir, project_root)

    agy_bin = settings.get("agy_binary", "agy")
    model = settings.get("model", "")
    mcp_server_name = settings.get("mcp_server_name", "")
    out_fmt = settings.get("output_format", "stream-json")
    timeout = int(settings.get("timeout_seconds", 300))

    for condition in cfg.get("conditions", []):
        cond_name = condition["name"]
        if args.condition and cond_name != args.condition:
            continue

        use_mcp = bool(condition.get("use_mcp", False))
        result_file = out_dir / f"{cond_name}.json"

        print("\n============================================================")
        print(f"CONDITION: {cond_name} (use_mcp={use_mcp}, model={model})")
        print("============================================================")

        set_mcp_state(agy_bin, mcp_server_name, enable=use_mcp)

        records = load_existing_records(result_file)
        completed_keys = {
            (r["repo_id"], r["question_id"]) for r in records if r.get("metrics", {}).get("status") == "SUCCESS"
        }
        if completed_keys and not args.force:
            print(f"[Resume] Đã tìm thấy {len(completed_keys)} câu hỏi hoàn tất trước đó, sẽ bỏ qua.")

        for repo in cfg.get("repositories", []):
            repo_id = repo["id"]
            working_dir = str(empty_dir) if use_mcp else repo["path"]

            if not Path(working_dir).exists():
                print(f"[Skip Repo] Thư mục không tồn tại: {working_dir}")
                continue

            for q in repo.get("questions", []):
                q_id = q["q_id"]
                if args.question and q_id != args.question:
                    continue

                if (repo_id, q_id) in completed_keys and not args.force:
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

                # Replace existing record for this question if it exists, otherwise append
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
