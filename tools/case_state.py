"""案例状态管理"""
from pathlib import Path
from typing import Any, Dict, List, Optional
from tools.io_utils import case_path, load_json, save_json


def init_state(project_root: Path, case_id: str) -> None:
    """初始化案例状态"""
    cp = case_path(project_root, case_id)
    state_file = cp / "state" / "case_state.json"
    state = {
        "case_id": case_id,
        "status": "created",
        "current_stage": "initialized",
        "iteration": 0,
        "history": [],
        "approvals": [],
    }
    save_json(state_file, state)


def update_state(
    project_root: Path,
    case_id: str,
    status: Optional[str] = None,
    current_stage: Optional[str] = None,
    iteration: Optional[int] = None,
    iteration_index: Optional[int] = None,
    last_tool: Optional[str] = None,
    next_tool: Optional[str] = None,
) -> Dict[str, Any]:
    """更新案例状态"""
    cp = case_path(project_root, case_id)
    state_file = cp / "state" / "case_state.json"
    state = load_json(state_file)

    if status is not None:
        state["status"] = status
    if current_stage is not None:
        state["current_stage"] = current_stage
    # 支持 iteration 和 iteration_index 两种参数名
    iter_val = iteration if iteration is not None else iteration_index
    if iter_val is not None:
        state["iteration"] = iter_val
    if last_tool is not None:
        state["last_tool"] = last_tool
    if next_tool is not None:
        state["next_tool"] = next_tool

    save_json(state_file, state)
    return state


def add_approval(
    project_root: Path,
    case_id: str,
    approval_type: str,
    approved: bool,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """添加审批记录"""
    cp = case_path(project_root, case_id)
    state_file = cp / "state" / "case_state.json"
    state = load_json(state_file)

    approval_record = {
        "type": approval_type,
        "approved": approved,
        "details": details or {},
    }
    state["approvals"].append(approval_record)
    save_json(state_file, state)
    return state


def get_state(project_root: Path, case_id: str) -> Dict[str, Any]:
    """获取案例状态"""
    cp = case_path(project_root, case_id)
    state_file = cp / "state" / "case_state.json"
    return load_json(state_file)


def load_state(project_root: Path, case_id: str) -> Dict[str, Any]:
    """兼容 API 层调用的状态读取函数。"""
    return get_state(project_root, case_id)
