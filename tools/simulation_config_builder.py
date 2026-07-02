"""仿真配置构建模块 - 根据需求自动设置边界条件、材料属性和求解参数"""
from pathlib import Path
from typing import Any, Dict
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def build_simulation_config(project_root: Path, case_id: str, iteration_index: int = 0) -> Dict[str, Any]:
    """构建仿真配置，包括边界条件、材料属性和求解参数"""
    cp = case_path(project_root, case_id)
    
    # 加载解析的需求
    req_file = cp / "work" / "parsed_requirement.json"
    if not req_file.exists():
        # 如果还没有解析需求，尝试从原始需求文件读取
        raw_req_file = cp / "input" / "requirement.txt"
        if raw_req_file.exists():
            # 使用默认配置
            parsed_req = {
                "environment_temp_c": 45,
                "chip_power_w": 80,
                "inlet_velocity_m_s": 2.0,
                "max_allowed_temp_c": 95,
                "heatsink_material": "aluminum_6061",
            }
        else:
            raise FileNotFoundError(f"Missing requirement file")
    else:
        parsed_req = load_json(req_file)
    
    # 加载几何信息
    geo_file = cp / "work" / "geometry_summary.json"
    geometry = load_json(geo_file) if geo_file.exists() else {}
    
    # 构建仿真配置
    config = {
        "iteration_index": iteration_index,
        "case_id": case_id,
        "boundary_conditions": {
            "inlet": {
                "type": "velocity_inlet",
                "velocity_m_s": parsed_req.get("inlet_velocity_m_s", 2.0),
                "temperature_c": parsed_req.get("environment_temp_c", 45),
                "turbulence_intensity": 0.05,
            },
            "outlet": {
                "type": "pressure_outlet",
                "gauge_pressure_pa": 0,
            },
            "walls": {
                "type": "wall",
                "thermal_condition": "adiabatic",
            },
            "heat_sources": [
                {
                    "name": "chip_heat_source",
                    "power_w": parsed_req.get("chip_power_w", 80),
                    "type": "constant_power",
                }
            ],
        },
        "materials": {
            "solid": {
                "heatsink": {
                    "material": parsed_req.get("heatsink_material", "aluminum_6061"),
                    "density_kg_m3": 2700,
                    "specific_heat_j_kg_k": 900,
                    "thermal_conductivity_w_m_k": 205,
                },
                "chip": {
                    "material": "silicon",
                    "density_kg_m3": 2330,
                    "specific_heat_j_kg_k": 700,
                    "thermal_conductivity_w_m_k": 148,
                },
            },
            "fluid": {
                "air": {
                    "material": "air",
                    "density_kg_m3": 1.225,
                    "specific_heat_j_kg_k": 1006,
                    "thermal_conductivity_w_m_k": 0.025,
                    "viscosity_kg_m_s": 1.789e-5,
                }
            },
        },
        "solver_settings": {
            "solver_type": "pressure_based",
            "time_formulation": "steady",
            "velocity_formulation": "absolute",
            "gradient_scheme": "least_squares_cell_based",
            "pressure_discretization": "second_order",
            "momentum_discretization": "second_order_upwind",
            "energy_discretization": "second_order_upwind",
            "turbulence_model": parsed_req.get("turbulence_model", "k-epsilon"),
            "radiation_model": "surface_to_surface" if parsed_req.get("radiation_enabled", True) else "none",
            "gravity": {
                "enabled": parsed_req.get("gravity_enabled", False),
                "vector": [0, 0, -9.81],
            },
        },
        "convergence_criteria": parsed_req.get("convergence_criteria", {
            "energy_residual": 1e-6,
            "velocity_residual": 1e-4,
            "temperature_monitor_max": 95.0,
        }),
        "mesh_settings": {
            "global_max_size_mm": 5.0,
            "global_min_size_mm": 0.5,
            "growth_rate": 1.2,
            "fin_cross_section_min_cells": 2,  # 散热鳍片横截面至少2个网格
            "boundary_layer_layers": 5,
            "boundary_layer_first_height_mm": 0.1,
        },
        "named_selections": geometry.get("named_selections_found", []),
    }
    
    # 保存配置
    out = cp / "work" / f"simulation_config_iter{iteration_index:03d}.json"
    iter_out = cp / "iterations" / f"iter_{iteration_index:03d}" / "simulation_config.json"
    save_json(out, config)
    save_json(iter_out, config)
    save_json(cp / "work" / "simulation_config.json", config)
    
    update_state(project_root, case_id, current_stage=f"simulation_config_built_iter{iteration_index:03d}", last_tool="build_simulation_config", next_tool="run_solver")
    log_decision(project_root, case_id, "ai", "simulation_config_built", {"path": str(out), "iteration": iteration_index})
    
    return {"status": "success", "config": config, "path": str(out)}
