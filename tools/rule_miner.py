from pathlib import Path
from typing import Any, Dict
from collections import Counter
from tools.io_utils import read_jsonl, save_json, append_jsonl


def mine_feedback_patterns(project_root: Path, min_count: int = 3) -> Dict[str, Any]:
    # 从 engineer_feedback.jsonl 里挖可规则化经验。
    # 这不是自动改规则，只输出 candidate_rule_updates.json 给人工 review。
    feedback = read_jsonl(project_root / "data" / "knowledge_db" / "engineer_feedback.jsonl")
    counter = Counter()
    examples = {}

    for fb in feedback:
        final_changes = fb.get("engineer_final_decision", {}).get("changes", [])
        for ch in final_changes:
            p = ch.get("parameter")
            if p:
                key = f"engineer_prefers::{p}"
                counter[key] += 1
                examples.setdefault(key, []).append(fb)

    candidates = []
    for key, count in counter.items():
        if count >= min_count:
            candidates.append({
                "candidate_rule": key,
                "support_count": count,
                "recommendation": "人工审查后，可加入 optimization_rules.json 或 prompts.py 约束。",
                "examples": examples[key][:3]
            })

    out = project_root / "data" / "knowledge_db" / "candidate_rule_updates.json"
    save_json(out, {"candidates": candidates, "feedback_count": len(feedback)})
    return {"status": "success", "candidate_count": len(candidates), "path": str(out), "candidates": candidates}


def record_rule_change(project_root: Path, rule_file: str, change_summary: str, author: str) -> Dict[str, Any]:
    record = {"rule_file": rule_file, "change_summary": change_summary, "author": author}
    append_jsonl(project_root / "data" / "knowledge_db" / "rule_change_log.jsonl", record)
    return {"status": "logged", "record": record}
