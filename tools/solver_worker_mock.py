"""求解器工作模块 - 模拟仿真计算过程"""
from pathlib import Path
from typing import Any, Dict
import time
from tools.io_utils import case_path, save_json, load_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def run_solver(project_root: Path, case_id: str, iteration_index: int = 0, approved: bool = True) -> Dict[str, Any]:
    """运行仿真求解器（模拟）"""
    cp = case_path(project_root, case_id)
    
    # 加载仿真配置
    config_file = cp / "work" / f"simulation_config_iter{iteration_index:03d}.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Missing simulation config: {config_file}")
    
    config = load_json(config_file)
    
    # 模拟网格划分过程
    mesh_result = _generate_mesh(cp, config.get("mesh_settings", {}), iteration_index)
    
    # 模拟求解计算过程
    print(f"[Solver] Starting simulation for case {case_id}, iteration {iteration_index}...")
    print(f"[Solver] Mesh generated with {mesh_result['cell_count']} cells")
    
    # 模拟迭代计算（简化版）
    max_iterations = 100
    for i in range(0, max_iterations + 1, 10):
        progress = i / max_iterations
        residuals = {
            "continuity": 1e-3 * (1 - progress) + 1e-6 * progress,
            "x_velocity": 1e-3 * (1 - progress) + 1e-5 * progress,
            "y_velocity": 1e-3 * (1 - progress) + 1e-5 * progress,
            "z_velocity": 1e-3 * (1 - progress) + 1e-5 * progress,
            "energy": 1e-3 * (1 - progress) + 1e-7 * progress,
            "k_epsilon": 1e-3 * (1 - progress) + 1e-5 * progress,
        }
        time.sleep(0.01)  # 模拟计算时间
    
    # 生成模拟结果
    solver_result = {
        "status": "converged",
        "iteration_index": iteration_index,
        "total_iterations": max_iterations,
        "computation_time_seconds": 45.3,
        "mesh_info": mesh_result,
        "final_residuals": {
            "continuity": 1e-6,
            "x_velocity": 1e-5,
            "y_velocity": 1e-5,
            "z_velocity": 1e-5,
            "energy": 1e-7,
            "k_epsilon": 1e-5,
        },
        "monitors": {
            "max_temperature_c": 87.5 + iteration_index * 2,  # 模拟温度变化
            "avg_temperature_c": 62.3 + iteration_index * 1.5,
            "pressure_drop_pa": 125.4,
            "mass_flow_rate_kg_s": 0.0034,
        },
        "convergence_achieved": True,
        "warnings": [],
    }
    
    # 保存结果
    out = cp / "results" / f"solver_result_iter{iteration_index:03d}.json"
    save_json(out, solver_result)
    
    print(f"[Solver] Simulation completed. Max temperature: {solver_result['monitors']['max_temperature_c']:.1f}°C")
    
    update_state(project_root, case_id, current_stage=f"solver_completed_iter{iteration_index:03d}", last_tool="run_solver")
    log_decision(project_root, case_id, "solver", "simulation_completed", {"path": str(out), "iterations": max_iterations})
    
    return {"status": "success", "result": solver_result, "path": str(out)}


def _generate_mesh(case_path: Path, mesh_settings: Dict[str, Any], iteration_index: int) -> Dict[str, Any]:
    """生成网格（模拟）"""
    # 基于配置生成网格信息
    base_cell_count = 500000
    fin_cells_bonus = mesh_settings.get("fin_cross_section_min_cells", 2) * 50000
    
    mesh_info = {
        "mesh_type": "polyhedral",
        "cell_count": base_cell_count + fin_cells_bonus + iteration_index * 10000,
        "face_count": base_cell_count * 5 + fin_cells_bonus * 5,
        "node_count": base_cell_count * 2 + fin_cells_bonus * 2,
        "quality_metrics": {
            "min_orthogonal_quality": 0.35,
            "max_skewness": 0.72,
            "aspect_ratio_max": 15.3,
        },
        "boundary_layers": {
            "layers": mesh_settings.get("boundary_layer_layers", 5),
            "first_height_mm": mesh_settings.get("boundary_layer_first_height_mm", 0.1),
            "growth_rate": mesh_settings.get("growth_rate", 1.2),
        },
        "refinement_regions": [
            {"name": "fin_region", "max_size_mm": mesh_settings.get("global_min_size_mm", 0.5)},
            {"name": "wake_region", "max_size_mm": 1.0},
        ],
    }
    
    # 保存网格信息
    mesh_file = case_path / "mesh" / f"mesh_info_iter{iteration_index:03d}.json"
    save_json(mesh_file, mesh_info)
    
    return mesh_info
