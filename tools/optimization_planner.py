"""优化规划模块 - 使用AI生成优化方案"""
from pathlib import Path
from typing import Any, Dict, List
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision
from agent.qwen_client import QwenClient


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
            "diagnosis": "passed",
            "reason": "Temperature requirement already met",
            "requires_review": False,
            "changes": [],
            "suggestions": [],
        }
    else:
        temperature_excess = current_max_temp - max_allowed_temp
        context = _build_llm_context(project_root, cp, case_id, iteration_index, result, parsed_req)
        try:
            ai_plan = QwenClient().make_optimization_plan(context)
            optimization_plan = _normalize_plan(
                ai_plan, context, case_id, iteration_index, current_max_temp, max_allowed_temp, temperature_excess
            )
            optimization_plan["planner_source"] = "qwen"
        except (RuntimeError, ValueError, TypeError) as exc:
            optimization_plan = _fallback_plan(
                parsed_req, case_id, iteration_index, current_max_temp, max_allowed_temp, temperature_excess, str(exc)
            )
    
    # 保存优化计划
    out = cp / "work" / f"optimization_plan_iter{iteration_index:03d}.json"
    iter_out = cp / "iterations" / f"iter_{iteration_index:03d}" / "optimization_plan.json"
    save_json(out, optimization_plan)
    save_json(iter_out, optimization_plan)
    save_json(cp / "work" / "latest_optimization_plan.json", optimization_plan)
    
    update_state(project_root, case_id, current_stage=f"optimization_planned_iter{iteration_index:03d}", last_tool="plan_optimization", next_tool="apply_optimization")
    log_decision(project_root, case_id, "ai", "optimization_plan_generated", {"path": str(out), "status": optimization_plan["status"]})
    
    return {"status": "success", "optimization_plan": optimization_plan, "path": str(out)}


def _build_llm_context(project_root: Path, cp: Path, case_id: str, iteration_index: int, solver_result: Dict[str, Any], parsed_req: Dict[str, Any]) -> Dict[str, Any]:
    iter_dir = cp / "iterations" / f"iter_{iteration_index:03d}"
    return {
        "case_id": case_id,
        "iteration_index": iteration_index,
        "requirements": parsed_req,
        "geometry_summary": load_json(cp / "work" / "geometry_summary.json"),
        "current_config": load_json(iter_dir / "simulation_config.json"),
        "current_result": load_json(iter_dir / "result_summary.json") or solver_result.get("monitors", {}),
        "solver_result": solver_result,
        "evaluation": load_json(iter_dir / "evaluation.json"),
        "optimization_rules": load_json(project_root / "rules" / "optimization_rules.json"),
        "previous_iterations": _previous_iterations(cp, iteration_index),
    }


def _normalize_plan(ai_plan: Dict[str, Any], context: Dict[str, Any], case_id: str, iteration_index: int, current_max_temp: float, max_allowed_temp: float, temperature_excess: float) -> Dict[str, Any]:
    rules = context.get("optimization_rules", {})
    levers = rules.get("design_levers", {})
    changes = []
    for change in ai_plan.get("changes", []):
        param = change.get("parameter")
        if param not in levers:
            continue
        lever = levers[param]
        new_value = _coerce_new_value(change.get("new_value"), lever)
        old_value = change.get("old_value", _current_value(context.get("current_config", {}), param, lever))
        requires_review = bool(change.get("requires_review")) or bool(lever.get("requires_approval")) or not bool(lever.get("auto_apply", False))
        changes.append({
            "parameter": param,
            "old_value": old_value,
            "new_value": new_value,
            "reason": change.get("reason", "Qwen 根据当前超温结果和优化规则建议调整。"),
            "requires_geometry_change": lever.get("type") == "geometry_parameter" or bool(change.get("requires_geometry_change")),
            "requires_review": requires_review,
        })
    requires_review = bool(ai_plan.get("requires_review")) or any(c["requires_review"] for c in changes)
    if not changes:
        requires_review = True
    return {
        "plan_id": f"{case_id}_opt_{iteration_index:03d}",
        "status": "required",
        "diagnosis": ai_plan.get("diagnosis", "design_failed_temperature_too_high"),
        "confidence": float(ai_plan.get("confidence", 0.5)),
        "current_max_temperature_c": current_max_temp,
        "target_max_temperature_c": max_allowed_temp,
        "temperature_excess_c": temperature_excess,
        "changes": changes,
        "risk_level": ai_plan.get("risk_level", "medium" if requires_review else "low"),
        "requires_review": requires_review,
        "expected_effect": ai_plan.get("expected_effect", {"temperature_reduction_direction": "down", "pressure_drop_direction": "up_or_same"}),
        "recommended_next_tool": ai_plan.get("recommended_next_tool", "apply_optimization_plan" if changes else "engineer_review"),
        "suggestions": ai_plan.get("suggestions", []),
        "recommended_actions": ai_plan.get("recommended_actions", []),
    }


def _fallback_plan(parsed_req: Dict[str, Any], case_id: str, iteration_index: int, current_max_temp: float, max_allowed_temp: float, temperature_excess: float, error: str) -> Dict[str, Any]:
    old_velocity = float(parsed_req.get("inlet_velocity_m_s", 2.0))
    new_velocity = min(3.0, old_velocity + 0.5)
    changes = []
    if new_velocity > old_velocity:
        changes.append({
            "parameter": "inlet_velocity_m_s",
            "old_value": old_velocity,
            "new_value": new_velocity,
            "reason": "Qwen 调用失败，使用保守兜底策略：小步提高入口风速。",
            "requires_geometry_change": False,
            "requires_review": False,
        })
    return {
        "plan_id": f"{case_id}_opt_{iteration_index:03d}",
        "status": "required",
        "diagnosis": "design_failed_temperature_too_high",
        "confidence": 0.3,
        "current_max_temperature_c": current_max_temp,
        "target_max_temperature_c": max_allowed_temp,
        "temperature_excess_c": temperature_excess,
        "changes": changes,
        "risk_level": "low" if changes else "medium",
        "requires_review": not changes,
        "expected_effect": {"temperature_reduction_direction": "down", "pressure_drop_direction": "up_or_same"},
        "recommended_next_tool": "apply_optimization_plan" if changes else "engineer_review",
        "suggestions": [],
        "recommended_actions": [],
        "planner_source": "fallback",
        "llm_error": error,
    }


def _coerce_new_value(value: Any, lever: Dict[str, Any]) -> Any:
    if "allowed_values" in lever:
        return value if value in lever["allowed_values"] else lever["allowed_values"][0]
    number = float(value if value is not None else lever.get("current_default", lever.get("min", 0)))
    return max(float(lever.get("min", number)), min(float(lever.get("max", number)), number))


def _current_value(config: Dict[str, Any], param: str, lever: Dict[str, Any]) -> Any:
    if param == "inlet_velocity_m_s":
        return config.get("boundary_conditions", {}).get("inlet", {}).get("velocity_m_s", lever.get("current_default"))
    if param == "heatsink_material":
        return config.get("materials", {}).get("solid", {}).get("heatsink", {}).get("material", lever.get("allowed_values", [""])[0])
    return config.get("design_variables", {}).get(param, lever.get("current_default"))


def _previous_iterations(cp: Path, current_index: int) -> List[Dict[str, Any]]:
    history = []
    for i in range(current_index):
        iter_dir = cp / "iterations" / f"iter_{i:03d}"
        history.append({
            "iteration_index": i,
            "result": load_json(iter_dir / "result_summary.json"),
            "evaluation": load_json(iter_dir / "evaluation.json"),
            "optimization_plan": load_json(iter_dir / "optimization_plan.json"),
        })
    return history
