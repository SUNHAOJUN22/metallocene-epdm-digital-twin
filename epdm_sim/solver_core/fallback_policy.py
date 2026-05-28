"""Fallback policy helpers for residual-aware solvers."""

from __future__ import annotations

from typing import Any

from ..residual_system import residual_system_acceptance
from .residual_projection import residual_projection_penalty


def fallback_policy_decision(result_or_system: Any, *, solver_failed: bool = False) -> dict[str, Any]:
    """Return whether a solver should warn/fallback from residual quality."""
    acceptance = residual_system_acceptance(getattr(result_or_system, "residual_system", result_or_system))
    penalty = residual_projection_penalty(result_or_system)
    should_fallback = bool(solver_failed or not acceptance["passed"] or penalty >= 1000.0)
    reasons = []
    if solver_failed:
        reasons.append("solver_failed")
    if not acceptance["passed"]:
        reasons.append("residual_acceptance_failed")
    if penalty >= 1000.0:
        reasons.append("critical_residual_penalty")
    return {
        "fallback_recommended": should_fallback,
        "reason": "; ".join(reasons) if reasons else "residuals accepted",
        "residual_penalty": float(penalty),
        "critical_count": int(acceptance.get("critical_count", 0)),
    }

