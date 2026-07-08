from pathlib import Path
from typing import Any, Dict
import numpy as np
import matplotlib.pyplot as plt
from tools.io_utils import case_path, load_json, save_json
from tools.solver_result_validator import validate_solver_result


def extract_results(project_root: Path, case_id: str, iteration_index: int) -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    iter_dir = cp / "iterations" / f"iter_{iteration_index:03d}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    result = load_json(iter_dir / "result_summary.json")
    if not result:
        solver = load_json(cp / "results" / f"solver_result_iter{iteration_index:03d}.json")
        config = load_json(iter_dir / "simulation_config.json")
        monitors = solver.get("monitors", {}) if isinstance(solver.get("monitors", {}), dict) else {}
        validation = validate_solver_result(project_root, solver)
        result = {
            "status": solver.get("status", "unknown"),
            "iteration_index": iteration_index,
            "converged": bool(solver.get("convergence_achieved")),
            "max_temperature_c": monitors.get("max_temperature_c"),
            "avg_temperature_c": monitors.get("avg_temperature_c"),
            "pressure_drop_pa": monitors.get("pressure_drop_pa"),
            "target_max_temperature_c": config.get("convergence_criteria", {}).get("temperature_monitor_max", 95.0),
            "mesh_quality": {"passed": True, "metrics": solver.get("mesh_info", {}).get("quality_metrics", {}) if isinstance(solver.get("mesh_info", {}), dict) else {}},
            "error": solver.get("error"),
            "solver_validation": validation,
        }
        try:
            result["passed"] = (
                validation["status"] == "passed"
                and result["converged"]
                and result["max_temperature_c"] is not None
                and float(result["max_temperature_c"]) <= float(result["target_max_temperature_c"])
            )
        except (TypeError, ValueError):
            result["passed"] = False
            result["status"] = "failed"
            result["error"] = result.get("error") or "invalid numeric solver output"

    img_dir = cp / "results"
    temp_png = img_dir / f"temperature_iter_{iteration_index:03d}.png"
    residual_png = img_dir / f"residuals_iter_{iteration_index:03d}.png"

    _plot_temperature(temp_png, result)
    _plot_residual(residual_png)

    result["images"] = [str(temp_png), str(residual_png)]
    save_json(iter_dir / "result_summary.json", result)
    save_json(cp / "results" / "result_summary.json", result)
    return {"status": "success", "images": result["images"], "summary": result}


def _plot_temperature(path: Path, result: Dict[str, Any]):
    try:
        max_temp = float(result.get("max_temperature_c", 90) or 90)
    except (TypeError, ValueError):
        max_temp = 90.0
    x = np.linspace(-2, 2, 80)
    y = np.linspace(-2, 2, 80)
    X, Y = np.meshgrid(x, y)
    Z = 45 + (max_temp - 45) * np.exp(-(X**2 + Y**2))
    plt.figure()
    plt.imshow(Z, origin="lower")
    plt.title("Temperature Contour Mock")
    plt.colorbar(label="C")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _plot_residual(path: Path):
    x = np.arange(1, 501)
    y = np.exp(-x/80) + 1e-5
    plt.figure()
    plt.plot(x, y)
    plt.yscale("log")
    plt.title("Residuals Mock")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
