from pathlib import Path
from typing import Any, Dict
import numpy as np
import matplotlib.pyplot as plt
from tools.io_utils import case_path, load_json, save_json


def extract_results(project_root: Path, case_id: str, iteration_index: int) -> Dict[str, Any]:
    cp = case_path(project_root, case_id)
    iter_dir = cp / "iterations" / f"iter_{iteration_index:03d}"
    result = load_json(iter_dir / "result_summary.json")

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
    max_temp = float(result.get("max_temperature_c", 90))
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
