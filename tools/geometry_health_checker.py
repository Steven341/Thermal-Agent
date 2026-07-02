from pathlib import Path
import shutil
from typing import Any, Dict
from tools.io_utils import case_path, load_json, save_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def geometry_health_check(project_root: Path, case_id: str) -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    rules = load_json(project_root / "rules" / "geometry_health_rules.json")
    geo = load_json(cp / "work" / "geometry_summary.json")
    clean = cp / "work" / "clean_model.step"

    found = set(geo.get("named_selections_found", []))
    missing = [x for x in rules["checks"]["required_named_selections"] if x not in found]

    checks = {
        "clean_model_file_exists": clean.exists(),
        "watertight": geo.get("health_mock", {}).get("watertight", True),
        "self_intersections": geo.get("health_mock", {}).get("self_intersections", 0),
        "named_selections_missing": missing,
        "volume_change_ratio": 0.02
    }

    passed = (
        checks["clean_model_file_exists"]
        and checks["watertight"]
        and checks["self_intersections"] == 0
        and not checks["named_selections_missing"]
        and checks["volume_change_ratio"] <= rules["checks"]["volume_change_ratio_limit"]
    )

    result = {
        "status": "passed" if passed else "failed",
        "checks": checks,
        "recommended_next_tool": "build_simulation_config" if passed else "rollback_geometry",
        "requires_review": not passed
    }

    if not passed and rules["on_fail"]["action"] == "rollback_to_original_model":
        original = cp / "input" / "model.step"
        if original.exists():
            shutil.copyfile(original, clean)
        result["rollback_done"] = True

    save_json(cp / "work" / "geometry_health_check.json", result)
    update_state(project_root, case_id, current_stage="geometry_health_checked", last_tool="geometry_health_check", next_tool=result["recommended_next_tool"])
    log_decision(project_root, case_id, "python", "geometry_health_checked", result)
    return result
