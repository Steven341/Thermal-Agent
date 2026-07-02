from pathlib import Path
from typing import Any, Dict


def run_regression_suite(project_root: Path, max_cases: int = 5) -> Dict[str, Any]:
    from workflow.thermal_pipeline import ThermalPipeline
    pipeline = ThermalPipeline(project_root)
    results = []
    case_ids = ["demo_001"][:max_cases]
    for case_id in case_ids:
        r = pipeline.run(case_id=case_id, approved=True, max_iterations=3)
        results.append({"case_id": case_id, "status": r.get("status"), "final_evaluation": r.get("final_evaluation")})
    passed = all(x["final_evaluation"] and x["final_evaluation"].get("passed") for x in results)
    return {"status": "passed" if passed else "failed", "results": results}
