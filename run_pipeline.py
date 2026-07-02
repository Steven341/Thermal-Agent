from pathlib import Path
from dotenv import load_dotenv
from workflow.thermal_pipeline import ThermalPipeline

load_dotenv()

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    result = ThermalPipeline(root).run("demo_001", approved=True, max_iterations=5)
    print("STATUS:", result["status"])
    print("FINAL_EVALUATION:", result.get("final_evaluation"))
    print("REPORT: cases/demo_001/report/report.docx")
    print("STATE: cases/demo_001/state/case_state.json")
    print("DECISION LOG: cases/demo_001/state/decision_log.jsonl")
