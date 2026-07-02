"""需求解析模块 - 使用AI解析客户需求"""
from pathlib import Path
from typing import Any, Dict
import re
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision
from agent.qwen_client import QwenClient


def parse_requirement(project_root: Path, case_id: str) -> Dict[str, Any]:
    """解析客户需求文档，提取仿真参数"""
    cp = case_path(project_root, case_id)
    req_file = cp / "input" / "requirement.txt"
    
    if not req_file.exists():
        raise FileNotFoundError(f"Missing requirement file: {req_file}")
    
    # 读取原始需求
    raw_text = req_file.read_text(encoding="utf-8")
    
    try:
        ai_result = QwenClient().parse_requirement(raw_text)
    except RuntimeError as exc:
        ai_result = _fallback_ai_requirement(raw_text)
        ai_result["llm_error"] = str(exc)
    parsed = _normalize_requirement(raw_text, ai_result)

    # 保存解析结果
    out = cp / "work" / "parsed_requirement.json"
    save_json(out, parsed)
    save_json(cp / "work" / "requirements.json", parsed)
    
    update_state(project_root, case_id, current_stage="requirement_parsed", last_tool="parse_requirement", next_tool="inspect_geometry")
    log_decision(project_root, case_id, "ai", "requirement_parsed", {"path": str(out), "key_params": list(parsed.keys()), "requires_review": parsed.get("requires_review")})
    
    return {"status": "success", "parsed_requirement": parsed, "path": str(out)}


def _normalize_requirement(raw_text: str, ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """将 Qwen 输出稳定映射到下游工具使用的字段。"""
    ambient = _number(ai_result.get("ambient_temperature_c"), 45)
    power = _number(ai_result.get("heat_source_power_w"), 80)
    velocity = _number(ai_result.get("inlet_velocity_m_s"), 2.0)
    max_temp = _number(ai_result.get("max_allowed_temperature_c"), 95)
    material_hint = str(ai_result.get("material_hint") or "")
    material = "aluminum_6061" if ("铝" in material_hint or "aluminum" in material_hint.lower()) else material_hint or "aluminum_6061"
    missing_fields = ai_result.get("missing_fields") or []
    parsed = {
        "raw_text": raw_text,
        "environment_temp_c": ambient,
        "chip_power_w": power,
        "inlet_velocity_m_s": velocity,
        "max_allowed_temp_c": max_temp,
        "heatsink_material": material,
        "fluid_type": "air",
        "gravity_enabled": False,
        "radiation_enabled": True,
        "turbulence_model": "k-epsilon",
        "convergence_criteria": {
            "energy_residual": 1e-6,
            "velocity_residual": 1e-4,
            "temperature_monitor_max": max_temp
        },
        "named_selections_required": ["inlet", "outlet", "chip_heat_source", "heatsink", "fluid_domain"],
        "product_type": ai_result.get("product_type", "plate_fin_heatsink"),
        "simulation_goal": ai_result.get("simulation_goal", f"max temperature <= {max_temp} C"),
        "missing_fields": missing_fields,
        "requires_review": bool(ai_result.get("requires_review", bool(missing_fields))),
        "llm_raw": ai_result,
    }
    return parsed


def _number(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else default


def _fallback_ai_requirement(text: str) -> Dict[str, Any]:
    def find_num(patterns, default):
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return float(match.group(1))
        return default

    target = find_num([r"最高温度.*?(\d+)", r"低于\s*(\d+)", r"under\s*(\d+)"], 95)
    return {
        "ambient_temperature_c": find_num([r"环境温度\s*(\d+)", r"ambient.*?(\d+)"], 45),
        "heat_source_power_w": find_num([r"功耗\s*(\d+)", r"(\d+)\s*W", r"power.*?(\d+)"], 80),
        "inlet_velocity_m_s": find_num([r"风速\s*(\d+(?:\.\d+)?)", r"velocity.*?(\d+(?:\.\d+)?)"], 2.0),
        "max_allowed_temperature_c": target,
        "material_hint": "铝合金" if ("铝" in text or "aluminum" in text.lower()) else "",
        "product_type": "plate_fin_heatsink",
        "simulation_goal": f"max temperature <= {target} C",
        "missing_fields": [],
        "requires_review": True,
    }
