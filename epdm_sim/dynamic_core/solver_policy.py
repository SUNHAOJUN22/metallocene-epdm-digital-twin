"""Closed-loop dynamic solver policy for V6.2."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .solver_decision import choose_dynamic_solver, dynamic_fallback_policy, dynamic_solver_decision_dataframe
from .stability_checks import dynamic_stability_status, stiffness_indicator_from_profile
from .state_invariants import state_invariants_status
from .step_acceptance import dynamic_step_acceptance_dataframe, dynamic_step_acceptance_summary


def choose_dynamic_solver_policy(
    dynamic_result: Any | None = None,
    *,
    stiffness_indicator: float | None = None,
    residual_acceptance_rate: float | None = None,
    invariant_violations: int = 0,
    event_risk: str = "low",
) -> dict[str, Any]:
    """Choose dynamic solver policy from stiffness, residuals, invariants and events."""
    if dynamic_result is not None:
        decision_df = dynamic_solver_decision_dataframe(dynamic_result)
        step_summary = dynamic_step_acceptance_summary(dynamic_result)
        invariant_status = state_invariants_status(dynamic_result)
        stiff = stiffness_indicator_from_profile(dynamic_result)
        residual_rate = float(decision_df.get("residual_acceptance_rate", pd.Series([step_summary["step_acceptance_rate"]])).iloc[0])
        inv_passed = bool(invariant_status.get("passed", False))
        risk = "high" if not inv_passed or step_summary["step_acceptance_rate"] < 0.5 else event_risk
        base = choose_dynamic_solver(stiffness_indicator=stiff, residual_acceptance_rate=residual_rate, invariants_passed=inv_passed, event_risk=risk)
    else:
        inv_passed = int(invariant_violations) == 0
        base = choose_dynamic_solver(
            stiffness_indicator=float(stiffness_indicator or 0.0),
            residual_acceptance_rate=float(1.0 if residual_acceptance_rate is None else residual_acceptance_rate),
            invariants_passed=inv_passed,
            event_risk=event_risk,
        )
        step_summary = {"step_acceptance_rate": float(1.0 if residual_acceptance_rate is None else residual_acceptance_rate), "step_count": 1}
    policy = dynamic_fallback_policy({"critical_residual_count": 0 if base["residual_acceptance_rate"] >= 0.5 else 1, "fallback_reason": base["solver_decision_reason"]})
    return {
        **base,
        **policy,
        "solver_policy_reason": base["solver_decision_reason"],
        "step_acceptance_rate": float(step_summary["step_acceptance_rate"]),
        "policy_passed": bool(base["residual_acceptance_rate"] >= 0.5 and step_summary["step_acceptance_rate"] >= 0.5),
    }


def dynamic_solver_policy_dataframe(dynamic_result: Any | None = None) -> pd.DataFrame:
    """Return dynamic solver policy rows."""
    policy = choose_dynamic_solver_policy(dynamic_result)
    stability = dynamic_stability_status(dynamic_result) if dynamic_result is not None else {"passed": True, "failed": 0}
    steps = dynamic_step_acceptance_summary(dynamic_result)
    return pd.DataFrame([{**policy, "stability_passed": bool(stability.get("passed", False)), "failed_stability_checks": int(stability.get("failed", 0)), **steps}])


def dynamic_solver_policy_report(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return compact report-safe dynamic solver policy status."""
    df = dynamic_solver_policy_dataframe(dynamic_result)
    row = df.iloc[0].to_dict()
    return {
        "selected_solver": row.get("selected_solver", "unknown"),
        "fallback_recommended": bool(row.get("fallback_recommended", False)),
        "solver_policy_reason": row.get("solver_policy_reason", ""),
        "step_acceptance_rate": float(row.get("step_acceptance_rate", 0.0)),
        "passed": bool(row.get("policy_passed", False)),
    }
