import json
from pathlib import Path


def load_json_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else []


def summarize(records: list[dict]) -> dict:
    valid = [r for r in records if r.get("metrics", {}).get("status") == "SUCCESS"]
    n = len(valid)
    if n == 0:
        return {"count": 0}

    total_tokens = sum(r["metrics"].get("usage", {}).get("total_tokens", 0) for r in valid)
    total_calls = sum(r["metrics"].get("tool_call_count", 0) for r in valid)
    total_mcp_calls = sum(r["metrics"].get("mcp_tool_call_count", 0) for r in valid)
    total_time = sum(r["metrics"].get("wall_clock_seconds", 0.0) for r in valid)

    return {
        "count": n,
        "avg_tokens": round(total_tokens / n, 1),
        "avg_tool_calls": round(total_calls / n, 2),
        "avg_mcp_calls": round(total_mcp_calls / n, 2),
        "avg_latency_sec": round(total_time / n, 2),
    }


def main():
    base_records = load_json_records(Path("./eval_results/antigravity_default.json"))
    mcp_records = load_json_records(Path("./eval_results/antigravity_mcp.json"))

    base_stats = summarize(base_records)
    mcp_stats = summarize(mcp_records)

    print("=== HEAD-TO-HEAD SUMMARY ===")
    print(f"Baseline (Default): {base_stats}")
    print(f"Treatment (MCP)   : {mcp_stats}")

    if base_stats.get("count") and mcp_stats.get("count"):
        tok_ratio = round(base_stats["avg_tokens"] / max(mcp_stats["avg_tokens"], 1), 2)
        call_ratio = round(base_stats["avg_tool_calls"] / max(mcp_stats["avg_tool_calls"], 0.1), 2)
        print(f"\n-> Token Reduction Ratio: {tok_ratio}x fewer tokens with MCP")
        print(f"-> Tool Call Ratio      : {call_ratio}x fewer tool calls with MCP")


if __name__ == "__main__":
    main()