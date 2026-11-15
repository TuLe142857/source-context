import json
from pathlib import Path

for fname in ["antigravity_default.jsonl", "antigravity_mcp.jsonl"]:
    p = Path("eval_results") / fname
    if not p.exists():
        continue
    fixed_lines = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        m = rec.get("metrics", {})
        # Bỏ qua dòng lỗi model cũ
        if m.get("status") == "ERROR":
            continue
        # Bóc tách lớp dict bị lồng bên trong m["response"]
        if isinstance(m.get("response"), dict):
            inner = m["response"]
            m["conversation_id"] = inner.get("conversation_id")
            m["status"] = inner.get("status")
            m["response"] = inner.get("response")
            m["cli_duration_seconds"] = inner.get("duration_seconds")
            m["num_turns"] = inner.get("num_turns")
            m["usage"] = inner.get("usage", {})
        fixed_lines.append(json.dumps(rec, ensure_ascii=False))
    p.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")
    print(f"Đã chuẩn hóa {len(fixed_lines)} bản ghi trong {p}")