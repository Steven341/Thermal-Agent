from pathlib import Path
import shutil
from typing import Any, Dict
from tools.io_utils import ensure_case_dirs
from tools.case_state import init_state
from tools.decision_logger import log_decision


def create_case(project_root: Path, case_id: str, overwrite: bool = False) -> Dict[str, Any]:
    cp = project_root / "cases" / case_id
    if cp.exists() and overwrite:
        shutil.rmtree(cp)
    ensure_case_dirs(project_root, case_id)

    req = cp / "input" / "requirement.txt"
    if not req.exists():
        req.write_text(
            "环境温度 45°C\n芯片功耗 80W\n入口风速 2m/s\n最高温度不能超过 95°C\n散热器材料铝合金\n",
            encoding="utf-8"
        )

    model = cp / "input" / "model.step"
    if not model.exists():
        model.write_text(
            "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('mock step'),'2;1');\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n",
            encoding="utf-8"
        )

    if not (cp / "state" / "case_state.json").exists():
        init_state(project_root, case_id)

    log_decision(project_root, case_id, "system", "case_created", {"path": str(cp)})
    return {"status": "ready", "case_id": case_id, "path": str(cp)}
