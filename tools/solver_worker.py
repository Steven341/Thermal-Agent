"""求解器入口：根据环境选择 mock 或真实 Ansys 适配器。"""
from pathlib import Path
from typing import Any, Dict
import os

from tools import solver_worker_ansys, solver_worker_mock


def run_solver(project_root: Path, case_id: str, iteration_index: int = 0, approved: bool = True) -> Dict[str, Any]:
    """运行求解器。

    默认使用 mock，真实部署时设置 MOCK_ANSYS=false 并配置 ANSYS_SOLVER_COMMAND。
    """
    use_mock = os.getenv("MOCK_ANSYS", "true").lower() == "true"
    if use_mock:
        return solver_worker_mock.run_solver(project_root, case_id, iteration_index=iteration_index, approved=approved)
    return solver_worker_ansys.run_solver(project_root, case_id, iteration_index=iteration_index, approved=approved)
