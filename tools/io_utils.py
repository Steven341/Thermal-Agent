"""基础IO工具函数"""
from pathlib import Path
import json
from typing import Any, Dict, List
import re

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_case_id(case_id: str) -> str:
    """Validate a case identifier before using it in filesystem paths.

    Real deployments receive case IDs from API clients, queues, and batch
    schedulers. Keeping IDs to a conservative filename-safe subset prevents
    path traversal and platform-specific surprises.
    """
    if not isinstance(case_id, str) or not _CASE_ID_RE.fullmatch(case_id):
        raise ValueError(
            "Invalid case_id. Use 1-128 characters: letters, numbers, dot, "
            "underscore, or hyphen; the first character must be alphanumeric."
        )
    return case_id


def ensure_case_dirs(project_root: Path, case_id: str) -> None:
    """确保案例目录结构存在"""
    cp = case_path(project_root, case_id)
    dirs = [
        cp / "input",
        cp / "output",
        cp / "state",
        cp / "report",
        cp / "mesh",
        cp / "results",
        cp / "work",
        cp / "iterations",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def case_path(project_root: Path, case_id: str) -> Path:
    """获取案例路径"""
    return project_root / "cases" / validate_case_id(case_id)


def load_json(path: Path) -> Dict[str, Any]:
    """加载JSON文件"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}, got {type(data).__name__}")
    return data


def save_json(path: Path, data: Dict[str, Any]) -> None:
    """保存JSON文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    """追加记录到JSONL文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """读取JSONL文件"""
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                records.append({"status": "invalid_jsonl", "line_number": line_number, "error": str(exc), "raw": line})
                continue
            if isinstance(record, dict):
                records.append(record)
            else:
                records.append({"status": "invalid_jsonl", "line_number": line_number, "error": "record is not a JSON object", "raw": record})
    return records
