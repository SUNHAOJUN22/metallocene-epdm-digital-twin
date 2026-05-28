"""Residual-aware dynamic solver decision helpers for V6.1."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_feedback import residual_feedback_solver_status
from .stability_checks import dynamic_stability_status, stiffness_indicator_from_profile


def choose_dynamic_solver(
    *,
    stiffness_indicator: float = 0.0,
    residual_acceptance_rate: float = 1.0,
    invariants_passed: bool = True,
    event_risk: str = "low",
) -> dict[str, Any]:
    """Choose RK45/BDF/explicit fallback from stiffness, residuals and events."""
    stiff = float(stiffness_indicator)
    residual_rate = float(np.clip(residual_acceptance_rate, 0.0, 1.0))
    high_event = str(event_risk).lower() in {"high", "runaway", "cooling_failure"}
    if residual_rate < 0.5 or not invariants_passed or high_event:
        solver = "explicit_bounded"
        reason = "fallback: residual acceptance, invariant or event risk requires bounded projection"
        fallback = True
    elif stiff > 1.0e5:
        solver = "solve_ivp_bdf"
        reason = "stiffness indicator favors BDF"
        fallback = False
    else:
        solver = "solve_ivp_rk45"
        reason = "non-stiff residual-accepted profile favors RK45"
        fallback = False
    return {
        "selected_solver": solver,
        "solver_decision_reason": reason,
        "fallback_recommended": fallback,
        "stiffness_indicator": stiff,
        "residual_acceptance_rate": residual_rate,
        "invariants_passed": bool(invariants_passed),
        "event_risk": event_risk,
    }


def dynamic_fallback_policy(status: dict[str, Any]) -> dict[str, Any]:
    """Return fallback policy from dynamic solver status fields."""
    critical = int(status.get("critical_residual_count", 0) or 0)
    fallback = bool(status.get("fallback_used", False) or critical > 0)
    reason = str(status.get("fallback_reason", ""))
    if critical > 0 and not reason:
        reason = "critical dynamic residual"
    return {"fallback_required": fallback, "fallback_reason": reason, "critical_residual_count": critical}


def residual_based_step_acceptance(residual_error: float, *, tolerance: float = 1.0e-6) -> dict[str, Any]:
    """Accept/reject one dynamic step based on residual error."""
    error = abs(float(residual_error))
    tol = float(tolerance)
    return {
        "residual_error": error,
        "tolerance": tol,
        "accepted": bool(np.isfinite(error) and error <= tol),
        "severity": "ok" if np.isfinite(error) and error <= tol else "warning",
    }


def dynamic_solver_decision_dataframe(dynamic_result: Any | None = None) -> pd.DataFrame:
    """Return solver decision rows for report/release gates."""
    if dynamic_result is None:
        decision = choose_dynamic_solver()
        return pd.DataFrame([{**decision, "status": "not_run"}])
    feedback = residual_feedback_solver_status(dynamic_result)
    stability = dynamic_stability_status(dynamic_result)
    stiff = stiffness_indicator_from_profile(dynamic_result)
    event_risk = "high" if not stability.get("passed", False) else "low"
    decision = choose_dynamic_solver(
        stiffness_indicator=stiff,
        residual_acceptance_rate=float(feedback.get("residual_acceptance_rate", 0.0)),
        invariants_passed=bool(stability.get("passed", False)),
        event_risk=event_risk,
    )
    policy = dynamic_fallback_policy(feedback)
    return pd.DataFrame([{**feedback, **stability, **decision, **policy, "status": "evaluated"}])
