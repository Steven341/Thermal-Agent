from pathlib import Path
from typing import Any, Dict
from tools.io_utils import case_path, save_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def inspect_geometry(project_root: Path, case_id: str) -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    model = cp / "input" / "model.step"
    if not model.exists():
        raise FileNotFoundError(f"Missing CAD file: {model}")

    geo = {
        "model_path": str(model),
        "geometry_type": "plate_fin_heatsink_mock",
        "parts": [
            {"name": "Heatsink_Base", "bbox_mm": [80, 40, 5], "type_guess": "heatsink_base", "thermal_importance": "high"},
            {"name": "Fin_Array", "bbox_mm": [80, 40, 18], "type_guess": "heatsink_fin", "thermal_importance": "high", "fin_count": 24, "fin_height_mm": 18, "fin_thickness_mm": 1.2, "fin_spacing_mm": 1.5},
            {"name": "Chip_Heat_Source", "bbox_mm": [20, 20, 1], "type_guess": "heat_source", "thermal_importance": "high"},
            {"name": "GB_M3_Screw", "bbox_mm": [1.8, 1.8, 4], "type_guess": "fastener", "thermal_importance": "low"}
        ],
        "holes": [{"hole_id": "H001", "diameter_mm": 3.0}, {"hole_id": "H002", "diameter_mm": 4.5}],
        "fillets": [{"edge_id": "F001", "radius_mm": 0.5}, {"edge_id": "F002", "radius_mm": 0.8}],
        "named_selections_found": ["inlet", "outlet", "chip_heat_source", "heatsink", "fluid_domain"],
        "named_selections_missing": [],
        "health_mock": {"watertight": True, "self_intersections": 0, "volume_mm3": 28450}
    }
    out = cp / "work" / "geometry_summary.json"
    save_json(out, geo)
    update_state(project_root, case_id, current_stage="geometry_inspected", last_tool="inspect_geometry", next_tool="generate_cleanup_plan")
    log_decision(project_root, case_id, "python", "geometry_inspected", {"path": str(out), "summary_keys": list(geo.keys())})
    return {"status": "success", "geometry": geo, "path": str(out)}
