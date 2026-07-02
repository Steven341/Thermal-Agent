from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone
from uuid import uuid4
from tools.io_utils import case_path, append_jsonl


def log_decision(project_root: Path, case_id: str, actor: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "actor": actor,
        "event_type": event_type,
        "payload": payload
    }
    cp = case_path(project_root, case_id)
    append_jsonl(cp / "state" / "decision_log.jsonl", event)
    append_jsonl(project_root / "logs" / "global_decision_log.jsonl", event)
    return event
