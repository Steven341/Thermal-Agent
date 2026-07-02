from pathlib import Path
import shutil
from typing import Any, Dict
from tools.io_utils import case_path, load_json, save_json
from tools.case_state import update_state, add_approval
from tools.decision_logger import log_decision


def execute_cleanup(project_root: Path, case_id: str, approved: bool, approver: str = "engineer") -> Dict[str, Any]:
    if not approved:
        update_state(project_root, case_id, status="waiting_for_approval", current_stage="cleanup_waiting_approval", next_tool="execute_cleanup")
        return {"status": "blocked", "reason": "execute_cleanup requires approval"}

    cp = case_path(project_root, case_id)
    src = cp / "input" / "model.step"
    dst = cp / "work" / "clean_model.step"
    plan = load_json(cp / "work" / "cleanup_plan.json")
    shutil.copyfile(src, dst)

    result = {
        "status": "success",
        "clean_model_path": str(dst),
        "mock": True,
        "deleted_parts_count": len(plan.get("delete_parts", [])),
        "filled_holes_count": len(plan.get("fill_holes", [])),
        "removed_fillets_count": len(plan.get("remove_fillets", []))
    }
    save_json(cp / "work" / "cleanup_result.json", result)
    add_approval(project_root, case_id, "execute_cleanup", "approved", approver)
    update_state(project_root, case_id, current_stage="cleanup_executed", last_tool="execute_cleanup", next_tool="geometry_health_check")
    log_decision(project_root, case_id, "engineer", "approval", {"tool": "execute_cleanup", "decision": "approved", "approver": approver})
    log_decision(project_root, case_id, "python", "cleanup_executed", result)
    return result
