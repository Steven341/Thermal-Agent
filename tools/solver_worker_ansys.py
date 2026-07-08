"""真实 Ansys 求解器适配层。

该模块负责把 Thermal Agent 生成的 simulation_config 交给外部 Ansys 自动化脚本。
外部脚本应读取配置 JSON，并输出与 solver_worker_mock 相同结构的 solver_result_iterXXX.json。
"""
from pathlib import Path
from typing import Any, Dict
import json
import os
import shlex
import subprocess

from tools.io_utils import case_path, load_json, save_json
from tools.case_state import update_state
from tools.decision_logger import log_decision


def run_solver(project_root: Path, case_id: str, iteration_index: int = 0, approved: bool = True) -> Dict[str, Any]:
    """调用真实 Ansys 自动化脚本运行网格与求解。

    真实部署需要配置：
    - MOCK_ANSYS=false
    - ANSYS_SOLVER_COMMAND=/path/to/run_ansys_solver.py 或可执行脚本

    脚本调用参数：
    --project-root <repo>
    --case-id <case_id>
    --iteration-index <i>
    --config <simulation_config_iterXXX.json>
    --output <solver_result_iterXXX.json>
    """
    if not approved:
        update_state(project_root, case_id, status="waiting_for_approval", current_stage="solver_waiting_approval", next_tool="run_solver")
        return {"status": "blocked", "reason": "real Ansys solver requires approval"}

    cp = case_path(project_root, case_id)
    config_file = cp / "work" / f"simulation_config_iter{iteration_index:03d}.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Missing simulation config: {config_file}")

    command = os.getenv("ANSYS_SOLVER_COMMAND", "").strip()
    if not command:
        raise RuntimeError("MOCK_ANSYS=false requires ANSYS_SOLVER_COMMAND to point to the Ansys automation entrypoint.")

    output_file = cp / "results" / f"solver_result_iter{iteration_index:03d}.json"
    cmd = shlex.split(command) + [
        "--project-root", str(project_root),
        "--case-id", case_id,
        "--iteration-index", str(iteration_index),
        "--config", str(config_file),
        "--output", str(output_file),
    ]
    try:
        timeout = int(os.getenv("ANSYS_SOLVER_TIMEOUT_SECONDS", "7200"))
    except ValueError:
        timeout = 7200
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        failure = {
            "status": "failed",
            "iteration_index": iteration_index,
            "error": f"Ansys solver timed out after {timeout} seconds",
            "stdout": exc.stdout,
            "stderr": exc.stderr,
            "command": cmd,
        }
        save_json(output_file, failure)
        update_state(project_root, case_id, current_stage=f"solver_timeout_iter{iteration_index:03d}", last_tool="run_solver")
        log_decision(project_root, case_id, "solver", "simulation_timeout", failure)
        return {"status": "failed", "result": failure, "path": str(output_file), "backend": "ansys"}

    if completed.returncode != 0:
        failure = {
            "status": "failed",
            "iteration_index": iteration_index,
            "error": completed.stderr or completed.stdout,
            "command": cmd,
        }
        save_json(output_file, failure)
        update_state(project_root, case_id, current_stage=f"solver_failed_iter{iteration_index:03d}", last_tool="run_solver")
        log_decision(project_root, case_id, "solver", "simulation_failed", failure)
        return {"status": "failed", "result": failure, "path": str(output_file)}

    solver_result = load_json(output_file)
    if not solver_result:
        try:
            solver_result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            failure = {
                "status": "failed",
                "iteration_index": iteration_index,
                "error": f"Solver completed but did not write valid JSON output: {exc}",
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "command": cmd,
            }
            save_json(output_file, failure)
            update_state(project_root, case_id, current_stage=f"solver_invalid_output_iter{iteration_index:03d}", last_tool="run_solver")
            log_decision(project_root, case_id, "solver", "simulation_invalid_output", failure)
            return {"status": "failed", "result": failure, "path": str(output_file), "backend": "ansys"}
        if not isinstance(solver_result, dict):
            failure = {"status": "failed", "iteration_index": iteration_index, "error": "Solver JSON output must be an object", "command": cmd}
            save_json(output_file, failure)
            return {"status": "failed", "result": failure, "path": str(output_file), "backend": "ansys"}
        save_json(output_file, solver_result)

    update_state(project_root, case_id, current_stage=f"solver_completed_iter{iteration_index:03d}", last_tool="run_solver")
    log_decision(project_root, case_id, "solver", "simulation_completed", {"path": str(output_file), "backend": "ansys"})
    return {"status": "success", "result": solver_result, "path": str(output_file), "backend": "ansys"}
