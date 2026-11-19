"""LLM-as-a-Judge Evaluation Runner for Source Context Benchmark.

Performs blind, single-answer evaluation of agent responses against ground truth
atomic checklists using an external LLM (e.g. OpenAI GPT-4o / GPT-4o-mini).
Preserves all original execution metrics (tool calls, tokens, latency) and enriches
records with structured judge scoring.
"""

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_env_credentials() -> tuple[str | None, str | None, str]:
    """Loads OpenAI API credentials from environment or .env files.

    Returns:
        tuple[str | None, str | None, str]: (api_key, base_url, model_name)
    """
    load_dotenv(".env.dev")
    load_dotenv(".env")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("SOURCE_CONTEXT_OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE_URL") or os.getenv("SOURCE_CONTEXT_OPENAI_API_BASE_URL")
    model = (
        os.getenv("OPENAI_MODEL")
        or os.getenv("SOURCE_CONTEXT_OPENAI_MODEL")
        or "gpt-4o-mini"
    )

    # Normalize placeholder keys
    if api_key == "changethis":
        api_key = None

    return api_key, base_url, model


def build_judge_prompt(
    question_text: str,
    ground_truth: dict[str, Any],
    candidate_response: str,
) -> list[dict[str, str]]:
    """Constructs a strict, blind evaluation prompt for the LLM judge.

    Args:
        question_text (str): The benchmark question prompt.
        ground_truth (dict[str, Any]): Ground truth dict containing target_files, target_symbols, and atomic_facts.
        candidate_response (str): The candidate agent's output response.

    Returns:
        list[dict[str, str]]: OpenAI chat messages.
    """
    target_symbols = ground_truth.get("target_symbols", [])
    target_files = ground_truth.get("target_files", [])
    atomic_facts = ground_truth.get("atomic_facts", [])

    system_prompt = (
        "You are an impartial, highly rigorous Code Intelligence Evaluation Judge.\n"
        "Your task is to grade an Agent's candidate response against a predefined Ground Truth Checklist.\n"
        "You must evaluate each atomic fact strictly and objectively based on clear evidence in the response.\n"
        "Do NOT penalize stylistic differences, but verify technical accuracy, function names, and file paths.\n"
        "Detect any hallucinations (invented functions, wrong files, false statements).\n"
        "You MUST return your verdict as a valid JSON object matching the requested schema."
    )

    facts_str = json.dumps(atomic_facts, ensure_ascii=False, indent=2)

    user_prompt = f"""[QUESTION]:
{question_text}

[TARGET SYMBOLS]:
{json.dumps(target_symbols, ensure_ascii=False)}

[TARGET FILES]:
{json.dumps(target_files, ensure_ascii=False)}

[GROUND TRUTH ATOMIC FACTS CHECKLIST]:
{facts_str}

[CANDIDATE RESPONSE]:
{candidate_response}

[INSTRUCTIONS]:
1. Evaluate each atomic fact individually. Set "passed": true ONLY if the Candidate Response explicitly
   and correctly states or identifies the fact. If missed or incorrect, set "passed": false.
2. In "evidence", quote or summarize the exact snippet from the Candidate Response that justifies your verdict.
3. Check for any hallucinated functions, classes, or files. If hallucinations exist,
   set "hallucination_detected": true and explain in "hallucination_details".
4. Calculate "total_score" (integer between 0 and 100):
   - Sum of the weights of all passed facts.
   - If hallucination_detected is true, deduct 25 points penalty (minimum 0).
5. Provide a concise 1-2 sentence overall summary in "justification".

[REQUIRED JSON SCHEMA]:
{{
  "evaluated_facts": [
    {{
      "id": "fact_id",
      "description": "fact description",
      "passed": true,
      "weight": 25,
      "evidence": "brief excerpt or explanation"
    }}
  ],
  "hallucination_detected": false,
  "hallucination_details": null,
  "total_score": 100,
  "justification": "Overall justification"
}}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def run_judge_on_record(
    client: OpenAI,
    model: str,
    record: dict[str, Any],
    ground_truth_map: dict[tuple[str, str], dict[str, Any]],
    temperature: float = 0.0,
    seed: int = 42,
) -> dict[str, Any] | None:
    """Evaluates a single record using the OpenAI judge.

    Args:
        client (OpenAI): OpenAI client instance.
        model (str): Judge model name.
        record (dict[str, Any]): Evaluation record.
        ground_truth_map (dict[tuple[str, str], dict[str, Any]]): Mapping from (repo_id, q_id) to ground truth.
        temperature (float): Sampling temperature (default 0.0).
        seed (int): Deterministic seed (default 42).

    Returns:
        dict[str, Any] | None: Judge evaluation payload or None if skipped.
    """
    repo_id = record.get("repo_id", "")
    q_id = record.get("question_id", "")
    key = (repo_id, q_id)

    gt = ground_truth_map.get(key)
    if not gt:
        logger.warning("No ground truth found for %s | %s. Skipping.", repo_id, q_id)
        return None

    metrics = record.get("metrics", {})
    if metrics.get("status") != "SUCCESS":
        # Failed execution automatically receives score 0
        return {
            "judge_model": model,
            "accuracy_score": 0,
            "total_facts": len(gt.get("atomic_facts", [])),
            "passed_facts": 0,
            "evaluated_facts": [],
            "hallucination_detected": False,
            "hallucination_details": None,
            "justification": f"Execution status was {metrics.get('status', 'FAILED')}.",
        }

    candidate_response = metrics.get("response", "")
    if not candidate_response or not candidate_response.strip():
        return {
            "judge_model": model,
            "accuracy_score": 0,
            "total_facts": len(gt.get("atomic_facts", [])),
            "passed_facts": 0,
            "evaluated_facts": [],
            "hallucination_detected": False,
            "hallucination_details": None,
            "justification": "Candidate response was empty.",
        }

    question_text = record.get("question_text", "")
    messages: Any = build_judge_prompt(question_text, gt, candidate_response)

    try:
        response: Any = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            seed=seed,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        passed_count = sum(1 for f in parsed.get("evaluated_facts", []) if f.get("passed"))
        total_facts = len(parsed.get("evaluated_facts", []))

        return {
            "judge_model": model,
            "accuracy_score": int(parsed.get("total_score", 0)),
            "total_facts": total_facts,
            "passed_facts": passed_count,
            "evaluated_facts": parsed.get("evaluated_facts", []),
            "hallucination_detected": bool(parsed.get("hallucination_detected", False)),
            "hallucination_details": parsed.get("hallucination_details"),
            "justification": parsed.get("justification", ""),
        }
    except Exception as exc:
        logger.error("Error calling judge LLM for %s | %s: %s", repo_id, q_id, exc)
        return None


def main() -> None:
    """Main CLI entrypoint for running the LLM-as-a-Judge benchmark."""
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge Benchmark Evaluator")
    parser.add_argument(
        "--config",
        type=str,
        default="evaluation/benchmark_config.yaml",
        help="Path to benchmark_config.yaml",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="evaluation/eval_results",
        help="Directory containing benchmark result JSON files",
    )
    parser.add_argument("--model", type=str, default=None, help="Judge model override")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API key override")
    parser.add_argument("--base-url", type=str, default=None, help="OpenAI API base URL override")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-judge all records even if already judged",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        return

    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 1. Resolve Ground Truth map
    ground_truth_map: dict[tuple[str, str], dict[str, Any]] = {}
    for repo in cfg.get("repositories", []):
        r_id = repo["id"]
        for q in repo.get("questions", []):
            if "ground_truth" in q:
                ground_truth_map[(r_id, q["q_id"])] = q["ground_truth"]

    logger.info("Loaded ground truth for %d benchmark questions.", len(ground_truth_map))

    # 2. Resolve Judge configuration and credentials
    env_key, env_base_url, env_model = load_env_credentials()
    judge_cfg = cfg.get("settings", {}).get("judge", {})

    api_key = args.api_key or env_key
    base_url = args.base_url or judge_cfg.get("base_url") or env_base_url
    model = args.model or judge_cfg.get("model") or env_model or "gpt-4o-mini"
    temperature = float(judge_cfg.get("temperature", 0.0))
    seed = int(judge_cfg.get("seed", 42))

    if not api_key:
        logger.error(
            "No OpenAI API key found! Please set OPENAI_API_KEY in your environment, "
            ".env.dev, or pass --api-key <YOUR_KEY>."
        )
        return

    client = OpenAI(
        api_key=api_key,
        base_url=base_url if base_url and "api.openai.com" not in base_url else None,
    )

    logger.info(
        "Initialized Judge Client | Model: %s | Base URL: %s | Temp: %.1f | Seed: %d",
        model,
        base_url or "https://api.openai.com/v1",
        temperature,
        seed,
    )

    # 3. Process candidate result JSON files in input-dir
    input_dir = Path(args.input_dir)
    target_files = [
        input_dir / "antigravity_mcp.json",
        input_dir / "antigravity_default.json",
    ]

    all_judged_records: list[dict[str, Any]] = []

    for file_path in target_files:
        if not file_path.exists():
            logger.warning("Target result file does not exist: %s. Skipping.", file_path)
            continue

        with open(file_path, encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, list):
            continue

        logger.info("Evaluating %d records in %s...", len(records), file_path.name)
        updated_count = 0

        for rec in records:
            cond = rec.get("condition", "unknown")
            r_id = rec.get("repo_id", "")
            q_id = rec.get("question_id", "")

            # Check if already judged
            existing_judge = rec.get("metrics", {}).get("judge")
            if existing_judge and not args.force:
                logger.info(
                    "[%s] %s | %s already judged (Score: %s). Skipping (use --force to re-judge).",
                    cond,
                    r_id,
                    q_id,
                    existing_judge.get("accuracy_score"),
                )
                all_judged_records.append(rec)
                continue

            logger.info("[%s] Judging %s | %s ...", cond, r_id, q_id)
            judge_res = run_judge_on_record(
                client=client,
                model=model,
                record=rec,
                ground_truth_map=ground_truth_map,
                temperature=temperature,
                seed=seed,
            )

            if judge_res:
                rec.setdefault("metrics", {})["judge"] = judge_res
                score = judge_res.get("accuracy_score", 0)
                passed = judge_res.get("passed_facts", 0)
                total = judge_res.get("total_facts", 0)
                logger.info(
                    "[%s] %s | %s -> Score: %d/100 (%d/%d facts passed)",
                    cond,
                    r_id,
                    q_id,
                    score,
                    passed,
                    total,
                )
                updated_count += 1

            all_judged_records.append(rec)

        # Save back to file, preserving all existing tool calls, tokens, and metadata
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info("Updated %d records in %s with judge evaluations.", updated_count, file_path.name)

    # Consolidated judge output file
    consolidated_path = input_dir / "judge_summary.json"
    judged_items = [
        {
            "condition": r.get("condition"),
            "repo_id": r.get("repo_id"),
            "question_id": r.get("question_id"),
            "dimension": r.get("dimension"),
            "judge": r.get("metrics", {}).get("judge"),
            "tool_call_count": r.get("metrics", {}).get("tool_call_count"),
            "total_tokens": r.get("metrics", {}).get("usage", {}).get("total_tokens"),
            "wall_clock_seconds": r.get("metrics", {}).get("wall_clock_seconds"),
        }
        for r in all_judged_records
        if r.get("metrics", {}).get("judge")
    ]
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(judged_items, f, ensure_ascii=False, indent=2)

    logger.info("Saved consolidated judge summary to %s", consolidated_path)


if __name__ == "__main__":
    main()
