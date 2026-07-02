from pathlib import Path
from typing import Any, Dict
from tools.io_utils import case_path, load_json, save_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def evaluate_result(project_root: Path, case_id: str, iteration_index: int) -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    result = load_json(cp / "iterations" / f"iter_{iteration_index:03d}" / "result_summary.json")

    if result.get("status") == "failed":
        evaluation = {"evaluation": "solver_failed", "passed": False, "reason": result.get("error", "solver failed"), "recommended_next_tool": "solver_log_parser", "requires_review": True}
    elif not result.get("mesh_quality", {}).get("passed", True):
        evaluation = {"evaluation": "bad_mesh", "passed": False, "reason": "mesh quality failed", "recommended_next_tool": "mesh_planner", "requires_review": True}
    elif not result.get("converged"):
        evaluation = {"evaluation": "not_converged", "passed": False, "reason": "not converged", "recommended_next_tool": "solver_settings_debugger", "requires_review": True}
    elif result["max_temperature_c"] > result["target_max_temperature_c"]:
        evaluation = {
            "evaluation": "design_failed",
            "passed": False,
            "reason": "max_temperature_exceeds_target",
            "max_temperature_c": result["max_temperature_c"],
            "target_max_temperature_c": result["target_max_temperature_c"],
            "recommended_next_tool": "optimization_planner",
            "requires_review": True
        }
    else:
        evaluation = {"evaluation": "passed", "passed": True, "reason": "target satisfied", "recommended_next_tool": "generate_report", "requires_review": False}

    save_json(cp / "iterations" / f"iter_{iteration_index:03d}" / "evaluation.json", evaluation)
    save_json(cp / "work" / "latest_evaluation.json", evaluation)
    update_state(project_root, case_id, current_stage="result_evaluated", last_tool="evaluate_result", next_tool=evaluation["recommended_next_tool"])
    log_decision(project_root, case_id, "python", "result_evaluated", {"iteration_index": iteration_index, "evaluation": evaluation})
    return evaluation
