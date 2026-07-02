"""几何清理规划模块 - 使用AI生成清理计划"""
from pathlib import Path
from typing import Any, Dict, List
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def generate_cleanup_plan(project_root: Path, case_id: str) -> Dict[str, Any]:
    """基于几何检查结果，生成清理计划"""
    cp = case_path(project_root, case_id)
    
    # 加载几何检查结果
    geo_file = cp / "work" / "geometry_summary.json"
    if not geo_file.exists():
        raise FileNotFoundError(f"Missing geometry summary: {geo_file}")
    
    geometry = load_json(geo_file)
    
    # 模拟AI生成的清理计划（实际应调用AI模型）
    cleanup_plan = {
        "plan_id": f"{case_id}_cleanup_001",
        "rules_applied": [
            {"rule_id": "R001", "description": "删除小于2x2x2mm的零件", "type": "size_filter", "params": {"min_size_mm": 2.0}},
            {"rule_id": "R002", "description": "删除名字带GB的标准件", "type": "name_filter", "params": {"pattern": "GB"}},
        ],
        "parts_to_remove": [],
        "holes_to_fill": [],
        "fillets_to_simplify": [],
    }
    
    # 根据规则识别需要清理的元素
    for part in geometry.get("parts", []):
        bbox = part.get("bbox_mm", [0, 0, 0])
        if all(dim < 2.0 for dim in bbox):
            cleanup_plan["parts_to_remove"].append({
                "part_name": part["name"],
                "reason": "size_below_threshold",
                "bbox_mm": bbox
            })
        elif "GB" in part.get("name", ""):
            cleanup_plan["parts_to_remove"].append({
                "part_name": part["name"],
                "reason": "standard_fastener",
                "bbox_mm": bbox
            })
    
    # 处理小孔（直径<5mm）
    for hole in geometry.get("holes", []):
        if hole.get("diameter_mm", 0) < 5.0:
            cleanup_plan["holes_to_fill"].append({
                "hole_id": hole["hole_id"],
                "diameter_mm": hole["diameter_mm"],
                "action": "fill"
            })
    
    # 处理圆角（简化为直角）
    for fillet in geometry.get("fillets", []):
        cleanup_plan["fillets_to_simplify"].append({
            "edge_id": fillet["edge_id"],
            "radius_mm": fillet["radius_mm"],
            "action": "convert_to_chamfer_or_remove"
        })
    
    # 保存清理计划
    out = cp / "work" / "cleanup_plan.json"
    save_json(out, cleanup_plan)
    
    update_state(project_root, case_id, current_stage="cleanup_plan_generated", last_tool="generate_cleanup_plan", next_tool="execute_cleanup")
    log_decision(project_root, case_id, "ai", "cleanup_plan_generated", {"path": str(out), "parts_to_remove_count": len(cleanup_plan["parts_to_remove"])})
    
    return {"status": "success", "cleanup_plan": cleanup_plan, "path": str(out)}
