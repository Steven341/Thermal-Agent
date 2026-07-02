from pathlib import Path
from typing import Any, Dict, List
from tools.io_utils import read_jsonl, append_jsonl, load_json
from tools.decision_logger import log_decision


def retrieve_similar_cases(project_root: Path, context: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
    db_path = project_root / "data" / "knowledge_db" / "case_index.jsonl"
    cases = read_jsonl(db_path)
    req = context.get("requirements", {})
    scored = []
    for c in cases:
        score = _score_case(req, c)
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, **c} for s, c in scored[:top_k]]


def add_case_to_knowledge_db(project_root: Path, case_id: str) -> Dict[str, Any]:
    cp = project_root / "cases" / case_id
    req = load_json(cp / "work" / "requirements.json")
    geo = load_json(cp / "work" / "geometry_summary.json")
    result = load_json(cp / "results" / "result_summary.json")
    state = load_json(cp / "state" / "case_state.json")

    record = {
        "case_id": case_id,
        "product_type": req.get("product_type", "unknown"),
        "requirements": req,
        "geometry_features": _extract_geometry_features(geo),
        "final_result": result,
        "iteration_count": state.get("iteration_index", 0),
        "tags": [req.get("product_type", "unknown"), "auto_logged"]
    }
    append_jsonl(project_root / "data" / "knowledge_db" / "case_index.jsonl", record)
    log_decision(project_root, case_id, "system", "knowledge_db_updated", record)
    return {"status": "success", "record": record}


def record_engineer_feedback(project_root: Path, case_id: str, iteration_index: int, ai_suggestion: Dict[str, Any], engineer_final_decision: Dict[str, Any], reason: str, engineer: str) -> Dict[str, Any]:
    record = {
        "case_id": case_id,
        "iteration_index": iteration_index,
        "ai_suggestion": ai_suggestion,
        "engineer_final_decision": engineer_final_decision,
        "reason": reason,
        "engineer": engineer
    }
    append_jsonl(project_root / "data" / "knowledge_db" / "engineer_feedback.jsonl", record)
    log_decision(project_root, case_id, "engineer", "feedback_recorded", record)
    return {"status": "success", "record": record}


def _score_case(req: Dict[str, Any], c: Dict[str, Any]) -> float:
    creq = c.get("requirements", {})
    score = 0.0
    if req.get("product_type") == c.get("product_type"):
        score += 2.0
    for key, scale in [("heat_source_power_w", 100), ("ambient_temperature_c", 50), ("inlet_velocity_m_s", 5)]:
        if key in req and key in creq:
            diff = abs(float(req[key]) - float(creq[key]))
            score += max(0, 1 - diff / scale)
    return round(score, 4)


def _extract_geometry_features(geo: Dict[str, Any]) -> Dict[str, Any]:
    fin = next((p for p in geo.get("parts", []) if p.get("type_guess") == "heatsink_fin"), {})
    return {
        "geometry_type": geo.get("geometry_type"),
        "fin_height_mm": fin.get("fin_height_mm"),
        "fin_spacing_mm": fin.get("fin_spacing_mm"),
        "fin_thickness_mm": fin.get("fin_thickness_mm")
    }
