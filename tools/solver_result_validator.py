"""Validation helpers for solver outputs.

These checks do not prove CFD/thermal accuracy. They provide a deployable
quality gate that catches common integration and numerical credibility issues
before the agent treats a real Ansys result as trustworthy.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.io_utils import load_json


REQUIRED_MONITORS = ("max_temperature_c", "avg_temperature_c", "pressure_drop_pa")


def validate_solver_result(project_root: Path, solver_result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate result schema and numerical credibility signals.

    The validator is intentionally conservative: it checks that the adapter
    returned the fields required by postprocessing, that mesh metrics satisfy
    configured thresholds, that residuals meet configured targets, and that
    optional balance metrics are within the solver policy.
    """
    solver_rules = load_json(project_root / "rules" / "solver_rules.json")
    mesh_rules = load_json(project_root / "rules" / "mesh_rules.json")
    steady_rules = solver_rules.get("steady_state_thermal", {})
    mesh_thresholds = mesh_rules.get("quality_thresholds", {})

    checks: List[Dict[str, Any]] = []
    checks.extend(_validate_required_monitors(solver_result))
    checks.extend(_validate_convergence(solver_result, steady_rules))
    checks.extend(_validate_mesh_quality(solver_result, mesh_thresholds))
    checks.extend(_validate_balance_metrics(solver_result, steady_rules))

    failed_checks = [check for check in checks if not check["passed"]]
    warning_checks = [check for check in checks if check.get("severity") == "warning" and not check["passed"]]
    blocking_failures = [check for check in failed_checks if check.get("severity") != "warning"]

    return {
        "status": "passed" if not blocking_failures else "failed",
        "checks": checks,
        "failed_checks": failed_checks,
        "warning_count": len(warning_checks),
        "blocking_failure_count": len(blocking_failures),
        "accuracy_note": (
            "Validation checks integration completeness, convergence, mesh quality, and balance metrics. "
            "It is not a replacement for benchmark correlation, mesh independence studies, "
            "or engineering review of physics assumptions."
        ),
    }


def _validate_required_monitors(solver_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    monitors = solver_result.get("monitors") if isinstance(solver_result.get("monitors"), dict) else {}
    checks = []
    for monitor in REQUIRED_MONITORS:
        value = monitors.get(monitor)
        checks.append({
            "name": f"monitor_present:{monitor}",
            "passed": _is_number(value),
            "severity": "error",
            "value": value,
            "message": f"Required numeric monitor '{monitor}' must be present.",
        })
    return checks


def _validate_convergence(solver_result: Dict[str, Any], steady_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    target = float(steady_rules.get("residual_target", 1e-5))
    residuals = solver_result.get("final_residuals") if isinstance(solver_result.get("final_residuals"), dict) else {}
    max_residual = _max_numeric(residuals.values())
    return [
        {
            "name": "convergence_flag",
            "passed": bool(solver_result.get("convergence_achieved")),
            "severity": "error",
            "value": solver_result.get("convergence_achieved"),
            "message": "Solver must explicitly report convergence_achieved=true.",
        },
        {
            "name": "residual_target",
            "passed": max_residual is not None and max_residual <= target,
            "severity": "error",
            "value": max_residual,
            "limit": target,
            "message": "Maximum final residual should meet solver residual target.",
        },
    ]


def _validate_mesh_quality(solver_result: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
    mesh_info = solver_result.get("mesh_info") if isinstance(solver_result.get("mesh_info"), dict) else {}
    metrics = mesh_info.get("quality_metrics") if isinstance(mesh_info.get("quality_metrics"), dict) else {}
    min_orth = metrics.get("min_orthogonal_quality")
    max_skew = metrics.get("max_skewness")
    max_aspect = metrics.get("aspect_ratio_max")
    return [
        {
            "name": "mesh_min_orthogonal_quality",
            "passed": _compare(min_orth, thresholds.get("minimum_orthogonal_quality", 0.1), op=">="),
            "severity": "error",
            "value": min_orth,
            "limit": thresholds.get("minimum_orthogonal_quality", 0.1),
            "message": "Mesh orthogonal quality must be above configured threshold.",
        },
        {
            "name": "mesh_max_skewness",
            "passed": _compare(max_skew, thresholds.get("maximum_skewness", 0.95), op="<="),
            "severity": "error",
            "value": max_skew,
            "limit": thresholds.get("maximum_skewness", 0.95),
            "message": "Mesh skewness must be below configured threshold.",
        },
        {
            "name": "mesh_max_aspect_ratio",
            "passed": _compare(max_aspect, thresholds.get("maximum_aspect_ratio", 100), op="<="),
            "severity": "warning",
            "value": max_aspect,
            "limit": thresholds.get("maximum_aspect_ratio", 100),
            "message": "High aspect ratio can be acceptable in boundary layers but should be reviewed.",
        },
    ]


def _validate_balance_metrics(solver_result: Dict[str, Any], steady_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    monitors = solver_result.get("monitors") if isinstance(solver_result.get("monitors"), dict) else {}
    energy_imbalance = monitors.get("energy_imbalance_percent")
    mass_imbalance = monitors.get("mass_imbalance_percent")
    limit = steady_rules.get("energy_imbalance_max_percent", 3.0)
    checks = []
    if energy_imbalance is None:
        checks.append({
            "name": "energy_imbalance_present",
            "passed": False,
            "severity": "warning",
            "value": None,
            "message": "Energy imbalance was not reported; accuracy cannot be fully assessed.",
        })
    else:
        checks.append({
            "name": "energy_imbalance_limit",
            "passed": _is_number(energy_imbalance) and _compare(abs(float(energy_imbalance)), limit, op="<="),
            "severity": "error",
            "value": energy_imbalance,
            "limit": limit,
            "message": "Energy imbalance must be within configured limit.",
        })
    if mass_imbalance is None:
        checks.append({
            "name": "mass_imbalance_present",
            "passed": False,
            "severity": "warning",
            "value": None,
            "message": "Mass imbalance was not reported; flow solution should be reviewed.",
        })
    return checks


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _max_numeric(values: Any) -> Optional[float]:
    numeric_values = []
    for value in values:
        if _is_number(value):
            numeric_values.append(abs(float(value)))
    return max(numeric_values) if numeric_values else None


def _compare(value: Any, limit: Any, op: str) -> bool:
    if not _is_number(value) or not _is_number(limit):
        return False
    numeric_value = float(value)
    numeric_limit = float(limit)
    if op == ">=":
        return numeric_value >= numeric_limit
    if op == "<=":
        return numeric_value <= numeric_limit
    raise ValueError(f"Unsupported comparison operator: {op}")
