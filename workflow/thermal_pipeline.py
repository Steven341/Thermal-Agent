from pathlib import Path
from typing import Any, Dict, List
import os

from tools import case_manager, requirement_parser, geometry_inspector, geometry_cleanup_planner
from tools import geometry_cleanup_executor, geometry_health_checker, simulation_config_builder
from tools import solver_worker_mock, postprocess, result_evaluator
from tools import optimization_context_builder, optimization_planner, config_modifier, report_generator
from tools.case_state import update_state


class ThermalPipeline:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    def run(self, case_id: str, approved: bool = False, max_iterations: int = 5) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []

        steps.append({"create_case": case_manager.create_case(self.project_root, case_id)})
        update_state(self.project_root, case_id, status="running", current_stage="pipeline_started")

        steps.append({"parse_requirement": requirement_parser.parse_requirement(self.project_root, case_id)})
        steps.append({"inspect_geometry": geometry_inspector.inspect_geometry(self.project_root, case_id)})
        steps.append({"generate_cleanup_plan": geometry_cleanup_planner.generate_cleanup_plan(self.project_root, case_id)})

        if not approved:
            update_state(self.project_root, case_id, status="waiting_for_approval", current_stage="cleanup_waiting_approval")
            return {"status": "waiting_for_approval", "blocked_at": "execute_cleanup", "steps": steps}

        steps.append({"execute_cleanup": geometry_cleanup_executor.execute_cleanup(self.project_root, case_id, approved=True)})
        health = geometry_health_checker.geometry_health_check(self.project_root, case_id)
        steps.append({"geometry_health_check": health})
        if health["status"] != "passed":
            return {"status": "failed", "failed_at": "geometry_health_check", "steps": steps}

        steps.append({"build_simulation_config": simulation_config_builder.build_simulation_config(self.project_root, case_id, iteration_index=0)})

        auto_apply = os.getenv("AUTO_APPLY_LOW_RISK_OPTIMIZATION", "true").lower() == "true"
        final_eval = None

        for i in range(max_iterations):
            steps.append({f"run_solver_iter_{i:03d}": solver_worker_mock.run_solver(self.project_root, case_id, iteration_index=i, approved=True)})
            steps.append({f"extract_results_iter_{i:03d}": postprocess.extract_results(self.project_root, case_id, iteration_index=i)})
            final_eval = result_evaluator.evaluate_result(self.project_root, case_id, iteration_index=i)
            steps.append({f"evaluate_result_iter_{i:03d}": final_eval})

            if final_eval.get("evaluation") == "passed":
                break

            if final_eval.get("evaluation") != "design_failed":
                break

            steps.append({f"build_optimization_context_iter_{i:03d}": optimization_context_builder.build_optimization_context(self.project_root, case_id, iteration_index=i)})
            plan_result = optimization_planner.plan_optimization(self.project_root, case_id, iteration_index=i)
            steps.append({f"plan_optimization_iter_{i:03d}": plan_result})

            if i + 1 >= max_iterations:
                break

            plan = plan_result["optimization_plan"]
            can_auto_apply = auto_apply and not plan.get("requires_review", True)
            apply_approved = approved if plan.get("requires_review", False) else can_auto_apply
            applied = config_modifier.apply_optimization_plan(
                self.project_root, case_id, from_iteration=i, to_iteration=i + 1, approved=apply_approved
            )
            steps.append({f"apply_optimization_iter_{i:03d}_to_{i+1:03d}": applied})
            if applied.get("status") == "blocked":
                return {"status": "waiting_for_optimization_approval", "iteration": i, "steps": steps}

        steps.append({"generate_report": report_generator.generate_report(self.project_root, case_id)})
        return {"status": "completed", "case_id": case_id, "final_evaluation": final_eval, "steps": steps}
