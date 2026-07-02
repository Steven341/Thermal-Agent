from pathlib import Path
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

from agent.schemas import CaseRequest, PipelineRequest, FeedbackRequest
from agent.qwen_client import QwenClient
from workflow.thermal_pipeline import ThermalPipeline
from tools import case_manager, rule_miner, regression_runner, knowledge_db
from tools.case_state import load_state
from tools.io_utils import read_jsonl

PROJECT_ROOT = Path(__file__).resolve().parent
pipeline = ThermalPipeline(PROJECT_ROOT)

app = FastAPI(title="Thermal Agent FDE V4 Qwen Self Optimizing", version="0.4.0")


@app.get("/")
def root():
    return {"service": "thermal_agent_fde_v4_qwen_self_optimizing", "docs": "/docs"}


@app.get("/llm/test_qwen")
def test_qwen():
    return QwenClient().test_connection()


@app.post("/cases/create")
def create_case(req: CaseRequest):
    return case_manager.create_case(PROJECT_ROOT, req.case_id)


@app.get("/cases/{case_id}/state")
def get_case_state(case_id: str):
    return load_state(PROJECT_ROOT, case_id)


@app.get("/cases/{case_id}/decision_log")
def get_decision_log(case_id: str):
    return read_jsonl(PROJECT_ROOT / "cases" / case_id / "state" / "decision_log.jsonl")


@app.post("/pipeline/run_self_optimizing")
def run_self_optimizing(req: PipelineRequest):
    try:
        return pipeline.run(case_id=req.case_id, approved=req.approved, max_iterations=req.max_iterations)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/feedback/engineer")
def record_feedback(req: FeedbackRequest):
    return knowledge_db.record_engineer_feedback(
        PROJECT_ROOT,
        case_id=req.case_id,
        iteration_index=req.iteration_index,
        ai_suggestion=req.ai_suggestion,
        engineer_final_decision=req.engineer_final_decision,
        reason=req.reason,
        engineer=req.engineer
    )


@app.post("/rules/mine_feedback")
def mine_feedback():
    return rule_miner.mine_feedback_patterns(PROJECT_ROOT, min_count=3)


@app.post("/regression/run")
def run_regression():
    return regression_runner.run_regression_suite(PROJECT_ROOT)
