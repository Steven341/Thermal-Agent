from pathlib import Path
from typing import Any, Dict
import copy
from tools.io_utils import case_path, load_json, save_json
from tools.case_state import update_state, add_approval
from tools.decision_logger import log_decision


def apply_optimization_plan(project_root: Path, case_id: str, from_iteration: int, to_iteration: int, approved: bool, approver: str = "engineer") -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    src_dir = cp / "iterations" / f"iter_{from_iteration:03d}"
    plan = load_json(src_dir / "optimization_plan.json")
    config = load_json(src_dir / "simulation_config.json")

    if plan.get("requires_review") and not approved:
        update_state(project_root, case_id, status="waiting_for_approval", current_stage="optimization_waiting_approval", next_tool="apply_optimization_plan")
        return {"status": "blocked", "reason": "optimization plan requires approval", "plan": plan}

    new_config = copy.deepcopy(config)
    applied = []
    for ch in plan.get("changes", []):
        param = ch["parameter"]
        new_value = ch["new_value"]
        if param == "inlet_velocity_m_s":
            new_config["boundary_conditions"]["inlet"]["velocity_m_s"] = new_value
        elif param == "heatsink_material":
            new_config["materials"]["solid"]["heatsink"]["material"] = new_value
        else:
            new_config["design_variables"][param] = new_value
        applied.append(ch)

    new_config["iteration_index"] = to_iteration
    dst_dir = cp / "iterations" / f"iter_{to_iteration:03d}"
    save_json(dst_dir / "simulation_config.json", new_config)
    save_json(cp / "work" / f"simulation_config_iter{to_iteration:03d}.json", new_config)
    save_json(cp / "work" / "simulation_config.json", new_config)

    if plan.get("requires_review"):
        add_approval(project_root, case_id, "apply_optimization_plan", True, {"approver": approver})

    result = {"status": "success", "from_iteration": from_iteration, "to_iteration": to_iteration, "applied_changes": applied, "new_config": new_config}
    save_json(dst_dir / "config_modifier_result.json", result)
    update_state(project_root, case_id, current_stage="optimization_applied", iteration_index=to_iteration, last_tool="apply_optimization_plan", next_tool="run_solver")
    log_decision(project_root, case_id, "python", "optimization_applied", result)
    return result
