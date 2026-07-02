"""优化规划模块 - 使用AI生成优化方案"""
from pathlib import Path
from typing import Any, Dict, List
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def plan_optimization(project_root: Path, case_id: str, iteration_index: int = 0) -> Dict[str, Any]:
    """基于仿真结果，生成优化计划"""
    cp = case_path(project_root, case_id)
    
    # 加载当前仿真结果
    result_file = cp / "results" / f"solver_result_iter{iteration_index:03d}.json"
    if not result_file.exists():
        raise FileNotFoundError(f"Missing solver result: {result_file}")
    
    result = load_json(result_file)
    
    # 加载需求
    req_file = cp / "work" / "parsed_requirement.json"
    parsed_req = load_json(req_file) if req_file.exists() else {}
    
    max_allowed_temp = parsed_req.get("max_allowed_temp_c", 95.0)
    current_max_temp = result.get("monitors", {}).get("max_temperature_c", 85.0)
    
    # 判断是否需要优化
    if current_max_temp <= max_allowed_temp:
        optimization_plan = {
            "plan_id": f"{case_id}_opt_{iteration_index:03d}",
            "status": "not_required",
            "reason": "Temperature requirement already met",
            "requires_review": False,
            "suggestions": [],
        }
    else:
        # 生成优化建议（模拟 AI 决策）
        temperature_excess = current_max_temp - max_allowed_temp
        
        suggestions = []
        
        # 根据温度超标程度生成不同的优化建议
        if temperature_excess > 10:
            suggestions.append({
                "id": "OPT001",
                "type": "geometry_modification",
                "description": "增加散热鳍片数量以提高散热面积",
                "parameters": {
                    "action": "increase_fin_count",
                    "current_fin_count": 24,
                    "proposed_fin_count": 32,
                    "expected_improvement_c": -8,
                },
                "priority": "high",
                "risk_level": "low",
            })
            suggestions.append({
                "id": "OPT002",
                "type": "boundary_condition_change",
                "description": "提高入口风速以增强对流换热",
                "parameters": {
                    "action": "increase_inlet_velocity",
                    "current_velocity_m_s": parsed_req.get("inlet_velocity_m_s", 2.0),
                    "proposed_velocity_m_s": 3.0,
                    "expected_improvement_c": -5,
                },
                "priority": "medium",
                "risk_level": "low",
            })
        elif temperature_excess > 5:
            suggestions.append({
                "id": "OPT003",
                "type": "material_change",
                "description": "更换为更高导热系数的材料",
                "parameters": {
                    "action": "change_material",
                    "current_material": "aluminum_6061",
                    "proposed_material": "copper",
                    "thermal_conductivity_current_w_m_k": 205,
                    "thermal_conductivity_proposed_w_m_k": 400,
                    "expected_improvement_c": -6,
                },
                "priority": "medium",
                "risk_level": "medium",
            })
        else:
            suggestions.append({
                "id": "OPT004",
                "type": "geometry_modification",
                "description": "优化散热鳍片间距以改善气流分布",
                "parameters": {
                    "action": "optimize_fin_spacing",
                    "current_spacing_mm": 1.5,
                    "proposed_spacing_mm": 2.0,
                    "expected_improvement_c": -3,
                },
                "priority": "low",
                "risk_level": "low",
            })
        
        optimization_plan = {
            "plan_id": f"{case_id}_opt_{iteration_index:03d}",
            "status": "required",
            "current_max_temperature_c": current_max_temp,
            "target_max_temperature_c": max_allowed_temp,
            "temperature_excess_c": temperature_excess,
            "requires_review": False,  # 低风险优化可自动应用
            "suggestions": suggestions,
            "recommended_actions": [s["id"] for s in suggestions[:2]],
        }
    
    # 保存优化计划
    out = cp / "work" / f"optimization_plan_iter{iteration_index:03d}.json"
    save_json(out, optimization_plan)
    
    update_state(project_root, case_id, current_stage=f"optimization_planned_iter{iteration_index:03d}", last_tool="plan_optimization", next_tool="apply_optimization")
    log_decision(project_root, case_id, "ai", "optimization_plan_generated", {"path": str(out), "status": optimization_plan["status"]})
    
    return {"status": "success", "optimization_plan": optimization_plan, "path": str(out)}
