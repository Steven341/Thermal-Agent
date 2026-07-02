"""基础IO工具函数"""
from pathlib import Path
import json
from typing import Any, Dict, List


def ensure_case_dirs(project_root: Path, case_id: str) -> None:
    """确保案例目录结构存在"""
    cp = project_root / "cases" / case_id
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
    return project_root / "cases" / case_id


def load_json(path: Path) -> Dict[str, Any]:
    """加载JSON文件"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
