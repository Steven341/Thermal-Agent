from pathlib import Path
from typing import Any, Dict
import os
from tools.io_utils import case_path, load_json, save_json
from tools.knowledge_db import retrieve_similar_cases
from tools.case_state import update_state
from tools.decision_logger import log_decision


def build_optimization_context(project_root: Path, case_id: str, iteration_index: int) -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    iter_dir = cp / "iterations" / f"iter_{iteration_index:03d}"

    context = {
        "case_id": case_id,
        "iteration_index": iteration_index,
        "requirements": load_json(cp / "work" / "requirements.json"),
        "geometry_summary": load_json(cp / "work" / "geometry_summary.json"),
        "current_config": load_json(iter_dir / "simulation_config.json"),
        "current_result": load_json(iter_dir / "result_summary.json"),
        "evaluation": load_json(iter_dir / "evaluation.json"),
        "optimization_rules": load_json(project_root / "rules" / "optimization_rules.json"),
        "material_database": load_json(project_root / "rules" / "material_database.json"),
        "previous_iterations": _load_previous_iterations(cp, iteration_index),
        "similar_cases": []
    }
    top_k = int(os.getenv("KNOWLEDGE_RETRIEVAL_TOP_K", "3"))
    context["similar_cases"] = retrieve_similar_cases(project_root, context, top_k=top_k)

    out = iter_dir / "optimization_context.json"
    save_json(out, context)
    save_json(cp / "work" / "optimization_context.json", context)
    update_state(project_root, case_id, current_stage="optimization_context_built", last_tool="build_optimization_context", next_tool="optimization_planner")
    log_decision(project_root, case_id, "python", "optimization_context_built", {"iteration_index": iteration_index, "similar_cases_count": len(context["similar_cases"])})
    return {"status": "success", "optimization_context": context, "path": str(out)}


def _load_previous_iterations(cp: Path, current_index: int):
    history = []
    for i in range(current_index):
        d = cp / "iterations" / f"iter_{i:03d}"
        if (d / "result_summary.json").exists():
            history.append({
                "iteration_index": i,
                "config": load_json(d / "simulation_config.json") if (d / "simulation_config.json").exists() else {},
                "result": load_json(d / "result_summary.json"),
                "evaluation": load_json(d / "evaluation.json") if (d / "evaluation.json").exists() else {}
            })
    return history
