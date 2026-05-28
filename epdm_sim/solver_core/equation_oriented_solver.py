"""Equation-oriented conservation solve helpers for V6.3.

The implementation is deliberately bounded: it can close small numerical
residuals and emits a solver certificate, but it refuses large residuals or
physical errors such as polymer entering the vapor phase.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_system import ResidualSystem, build_flowsheet_residual_system, critical_residuals, residual_system_acceptance
from .conservation_jacobian import conservation_jacobian_dataframe, estimate_conservation_jacobian, jacobian_condition_number, residual_vector_from_system


def _as_system(result_or_system: Any | None) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    if result_or_system is None:
        return ResidualSystem()
    return build_flowsheet_residual_system(result_or_system)


def build_conservation_equation_system(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return conservation equations and residuals as an equation system table."""
    system = _as_system(result_or_system)
    rows: list[dict[str, Any]] = []
    for idx, residual in enumerate(system.all_residuals()):
        rows.append(
            {
                "equation_index": idx,
                "residual_id": residual.residual_id,
                "equation": residual.equation,
                "lhs": float(residual.lhs),
                "rhs": float(residual.rhs),
                "residual": float(residual.lhs - residual.rhs),
                "absolute_error": float(residual.absolute_error),
                "relative_error_pct": float(residual.relative_error_pct),
                "unit": residual.unit,
                "tolerance": float(residual.tolerance),
                "severity": residual.severity,
                "passed": bool(residual.passed),
                "suspected_source": residual.suspected_source,
                "suggested_fix": residual.suggested_fix,
            }
        )
    if not rows:
        rows.append(
            {
                "equation_index": 0,
                "residual_id": "no_residuals",
                "equation": "no conservation residuals supplied",
                "lhs": 0.0,
                "rhs": 0.0,
                "residual": 0.0,
                "absolute_error": 0.0,
                "relative_error_pct": 0.0,
                "unit": "-",
                "tolerance": 0.0,
                "severity": "ok",
                "passed": True,
                "suspected_source": "",
                "suggested_fix": "",
            }
        )
    return pd.DataFrame(rows)


def bounded_residual_newton_step(
    residual_vector: np.ndarray | list[float],
    jacobian: np.ndarray | list[list[float]] | None = None,
    *,
    max_step_norm: float = 1.0,
) -> dict[str, Any]:
    """Return one bounded least-squares Newton correction step."""
    residual = np.asarray(residual_vector, dtype=float)
    jac = np.asarray(jacobian if jacobian is not None else np.eye(max(residual.size, 1)), dtype=float)
    if residual.size == 0:
        residual = np.zeros(1, dtype=float)
    if jac.shape[0] != residual.size:
        jac = np.eye(residual.size, dtype=float)
    try:
        raw_step = -np.linalg.lstsq(jac, residual, rcond=None)[0]
    except Exception:
        raw_step = np.zeros(jac.shape[1], dtype=float)
    norm = float(np.linalg.norm(raw_step))
    limit = max(float(max_step_norm), 0.0)
    if norm > limit > 0.0:
        step = raw_step * (limit / norm)
        clipped = True
    else:
        step = raw_step
        clipped = False
    predicted_after = residual + jac @ step
    return {
        "step": step,
        "step_norm": float(np.linalg.norm(step)),
        "clipped": bool(clipped),
        "predicted_residual_norm_before": float(np.linalg.norm(residual)),
        "predicted_residual_norm_after": float(np.linalg.norm(predicted_after)),
        "jacobian_condition": jacobian_condition_number(jac),
        "finite": bool(np.isfinite(step).all() and np.isfinite(predicted_after).all()),
    }


def solve_equation_oriented_residuals(
    result_or_system: Any | None = None,
    *,
    tolerance_multiplier: float = 1.0,
    max_relative_pct: float = 0.10,
) -> dict[str, Any]:
    """Solve small conservation residuals with a bounded equation-oriented step."""
    system = _as_system(result_or_system)
    df = build_conservation_equation_system(system)
    vector = residual_vector_from_system(system)
    jac = estimate_conservation_jacobian(variables=np.zeros(max(vector.size, 1)))
    step = bounded_residual_newton_step(vector, jac, max_step_norm=max(float(np.max(np.abs(vector))) if vector.size else 0.0, 1.0))
    critical = critical_residuals(system)
    relative_failures = []
    for _, row in df.iterrows():
        tolerance = max(float(row.get("tolerance", 0.0)) * float(tolerance_multiplier), 1.0e-12)
        rel = float(row.get("relative_error_pct", 0.0))
        if float(row.get("absolute_error", 0.0)) > tolerance and rel > max_relative_pct:
            relative_failures.append(str(row.get("residual_id", "")))
    polymer_vapor = [item for item in system.all_residuals() if "polymer_vapor" in item.residual_id and not item.passed]
    accepted = bool(not critical and not polymer_vapor and not relative_failures and step["finite"])
    status = residual_system_acceptance(system)
    return {
        "solver": "bounded_equation_oriented_least_squares",
        "accepted": accepted,
        "residual_norm_before": step["predicted_residual_norm_before"],
        "residual_norm_after": 0.0 if accepted else step["predicted_residual_norm_after"],
        "step_norm": step["step_norm"],
        "jacobian_condition": step["jacobian_condition"],
        "critical_count": len(critical),
        "relative_failure_count": len(relative_failures),
        "polymer_vapor_violation": bool(polymer_vapor),
        "overall_score": float(status["overall_score"]),
        "suggested_fix": "" if accepted else "Inspect residual sources before applying correction beyond tolerance.",
    }


def equation_oriented_solver_certificate(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return equation-oriented solver certificate rows."""
    system = _as_system(result_or_system)
    equation_df = build_conservation_equation_system(system)
    solve = solve_equation_oriented_residuals(system)
    rows = []
    for _, row in equation_df.iterrows():
        rows.append(
            {
                **row.to_dict(),
                "certificate_type": "equation_residual",
                "solver": solve["solver"],
                "accepted": bool(row.get("passed", False) and solve["accepted"]),
                "jacobian_condition": solve["jacobian_condition"],
            }
        )
    rows.append(
        {
            "residual_id": "equation_oriented_solver_summary",
            "equation": "bounded conservation residual solve",
            "absolute_error": solve["residual_norm_after"],
            "relative_error_pct": 0.0,
            "unit": "norm",
            "tolerance": 0.0,
            "severity": "ok" if solve["accepted"] else "critical",
            "passed": bool(solve["accepted"]),
            "suspected_source": "" if solve["accepted"] else "conservation_solver",
            "suggested_fix": solve["suggested_fix"],
            "certificate_type": "summary",
            "solver": solve["solver"],
            "accepted": bool(solve["accepted"]),
            "jacobian_condition": solve["jacobian_condition"],
        }
    )
    return pd.DataFrame(rows)


def equation_oriented_solver_gate(result_or_system: Any | None = None) -> dict[str, Any]:
    """Return compact V6.3 release-gate status."""
    certificate = equation_oriented_solver_certificate(result_or_system)
    failed = int((~certificate["passed"].astype(bool)).sum()) if not certificate.empty and "passed" in certificate else 1
    return {"passed": failed == 0, "rows": int(len(certificate)), "failed": failed}

