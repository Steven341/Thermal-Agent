"""需求解析模块 - 使用AI解析客户需求"""
from pathlib import Path
from typing import Any, Dict
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def parse_requirement(project_root: Path, case_id: str) -> Dict[str, Any]:
    """解析客户需求文档，提取仿真参数"""
    cp = case_path(project_root, case_id)
    req_file = cp / "input" / "requirement.txt"
    
    if not req_file.exists():
        raise FileNotFoundError(f"Missing requirement file: {req_file}")
    
    # 读取原始需求
    raw_text = req_file.read_text(encoding="utf-8")
    
    # 模拟AI解析结果（实际应调用AI模型）
    parsed = {
        "raw_text": raw_text,
        "environment_temp_c": 45,
        "chip_power_w": 80,
        "inlet_velocity_m_s": 2.0,
        "max_allowed_temp_c": 95,
        "heatsink_material": "aluminum_6061",
        "fluid_type": "air",
        "gravity_enabled": False,
        "radiation_enabled": True,
        "turbulence_model": "k-epsilon",
        "convergence_criteria": {
            "energy_residual": 1e-6,
            "velocity_residual": 1e-4,
            "temperature_monitor_max": 95.0
        },
        "named_selections_required": ["inlet", "outlet", "chip_heat_source", "heatsink", "fluid_domain"],
    }
    
    # 保存解析结果
    out = cp / "work" / "parsed_requirement.json"
    save_json(out, parsed)
    
    update_state(project_root, case_id, current_stage="requirement_parsed", last_tool="parse_requirement", next_tool="inspect_geometry")
    log_decision(project_root, case_id, "ai", "requirement_parsed", {"path": str(out), "key_params": list(parsed.keys())})
    
    return {"status": "success", "parsed_requirement": parsed, "path": str(out)}
