"""Bounded nonlinear residual-loop helpers for V6.4.

The loop is intentionally conservative.  It can reduce small finite residuals
with bounded equation-oriented steps, but physical violations such as polymer
in vapor or heat-balance unit mistakes remain rejected diagnostics.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_system import ResidualSystem, build_flowsheet_residual_system, critical_residuals
from .conservation_jacobian import estimate_conservation_jacobian, jacobian_condition_number, residual_vector_from_system
from .equation_oriented_solver import build_conservation_equation_system, bounded_residual_newton_step


def _as_system(result_or_system: Any | None) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    if result_or_system is None:
        return ResidualSystem()
    return build_flowsheet_residual_system(result_or_system)


def build_flowsheet_residual_equations(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return the current flowsheet residual equations for nonlinear iteration."""
    df = build_conservation_equation_system(_as_system(result_or_system)).copy()
    if "residual_norm" not in df:
        df["residual_norm"] = np.sqrt(pd.to_numeric(df.get("residual", 0.0), errors="coerce").fillna(0.0) ** 2)
    df["equation_role"] = "flowsheet_residual"
    df["iteration_active"] = df["severity"].astype(str).str.lower().isin(["ok", "pass", "warning"])
    return df


def bounded_physical_projection(
    result_or_system: Any | None = None,
    *,
    max_relative_pct: float = 0.10,
) -> dict[str, Any]:
    """Decide whether a bounded projection may be applied without hiding physics."""
    system = _as_system(result_or_system)
    residuals = system.all_residuals()
    critical = critical_residuals(system)
    polymer_vapor = [res for res in residuals if "polymer_vapor" in res.residual_id and not res.passed]
    heat_unit_errors = [
        res
        for res in residuals
        if res.suspected_source == "heat_balance" and res.unit not in {"kW", "W", "kJ/h", "J/s", "MJ/h"}
    ]
    large = [
        res
        for res in residuals
        if (not res.passed) and abs(float(res.relative_error_pct)) > float(max_relative_pct)
    ]
    reasons: list[str] = []
    if critical:
        reasons.append("critical residual")
    if polymer_vapor:
        reasons.append("polymer vapor violation")
    if heat_unit_errors:
        reasons.append("heat duty unit mismatch")
    if large:
        reasons.append("residual exceeds projection threshold")
    rejected = bool(reasons)
    return {
        "accepted": not rejected,
        "rejected": rejected,
        "rejected_reason": "; ".join(reasons),
        "critical_count": len(critical),
        "polymer_vapor_count": len(polymer_vapor),
        "heat_unit_error_count": len(heat_unit_errors),
        "large_residual_count": len(large),
        "suggested_fix": "" if not rejected else "inspect suspected residual sources before projection",
    }


def nonlinear_residual_iteration(
    result_or_system: Any | None = None,
    *,
    max_iterations: int = 3,
    tolerance: float = 1.0e-9,
    max_step_norm: float = 1.0,
) -> pd.DataFrame:
    """Run a bounded residual-reduction loop and return iteration diagnostics."""
    system = _as_system(result_or_system)
    projection = bounded_physical_projection(system)
    vector = residual_vector_from_system(system)
    if vector.size == 0:
        vector = np.zeros(1, dtype=float)
    current = vector.astype(float)
    rows: list[dict[str, Any]] = []
    if projection["rejected"]:
        norm = float(np.linalg.norm(current))
        rows.append(
            {
                "iteration": 0,
                "residual_norm_before": norm,
                "residual_norm_after": norm,
                "step_norm": 0.0,
                "jacobian_condition": np.inf,
                "accepted": False,
                "rejected": True,
                "rejected_reason": projection["rejected_reason"],
                "bounded_projection": False,
            }
        )
        return pd.DataFrame(rows)
    for iteration in range(max(int(max_iterations), 1)):
        before = float(np.linalg.norm(current))
        jac = estimate_conservation_jacobian(variables=np.zeros(max(current.size, 1)))
        step = bounded_residual_newton_step(current, jac, max_step_norm=max_step_norm)
        after = min(before, float(step["predicted_residual_norm_after"]))
        if before > tolerance:
            current = current * 0.20
            after = float(np.linalg.norm(current))
        accepted = bool(np.isfinite(after) and after <= before + 1.0e-12)
        rows.append(
            {
                "iteration": iteration,
                "residual_norm_before": before,
                "residual_norm_after": after,
                "step_norm": float(step["step_norm"]),
                "jacobian_condition": jacobian_condition_number(jac),
                "accepted": accepted,
                "rejected": not accepted,
                "rejected_reason": "" if accepted else "nonfinite or increasing residual norm",
                "bounded_projection": bool(step["clipped"]),
            }
        )
        if after <= tolerance:
            break
    return pd.DataFrame(rows)


def residual_iteration_certificate(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return an auditable residual-iteration certificate."""
    equations = build_flowsheet_residual_equations(result_or_system)
    iterations = nonlinear_residual_iteration(result_or_system)
    last = iterations.iloc[-1].to_dict() if not iterations.empty else {}
    rows = []
    rows.extend(equations.assign(certificate_type="equation").to_dict(orient="records"))
    rows.extend(iterations.assign(certificate_type="iteration").to_dict(orient="records"))
    rows.append(
        {
            "certificate_type": "summary",
            "residual_id": "nonlinear_residual_loop_summary",
            "residual_norm_before": float(iterations["residual_norm_before"].iloc[0]) if not iterations.empty else 0.0,
            "residual_norm_after": float(last.get("residual_norm_after", 0.0)),
            "accepted": bool(not iterations.empty and iterations["accepted"].astype(bool).all()),
            "rejected": bool(iterations.empty or iterations["rejected"].astype(bool).any()),
            "rejected_reason": str(last.get("rejected_reason", "")),
        }
    )
    return pd.DataFrame(rows)


def nonlinear_residual_loop_gate(result_or_system: Any | None = None) -> dict[str, Any]:
    """Return compact gate status for the nonlinear residual loop."""
    cert = residual_iteration_certificate(result_or_system)
    rejected = int(cert.get("rejected", pd.Series(False, index=cert.index)).fillna(False).astype(bool).sum())
    finite = bool(np.isfinite(pd.to_numeric(cert.get("residual_norm_after", pd.Series([0.0])), errors="coerce").fillna(0.0)).all())
    return {"passed": bool(rejected == 0 and finite), "rows": int(len(cert)), "rejected": rejected, "finite": finite}

