"""Adaptive step-control diagnostics for V6.3 dynamic models."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .solver_policy import choose_dynamic_solver_policy
from .step_acceptance import dynamic_step_acceptance_dataframe


def adaptive_step_decision(
    residual_error: float,
    *,
    tolerance: float = 1.0e-6,
    invariant_passed: bool = True,
    stiffness_indicator: float = 0.0,
    event_risk: str = "low",
) -> dict[str, Any]:
    """Return one adaptive accept/reject decision."""
    policy = choose_dynamic_solver_policy(
        stiffness_indicator=stiffness_indicator,
        residual_acceptance_rate=1.0 if abs(float(residual_error)) <= float(tolerance) else 0.0,
        invariant_violations=0 if invariant_passed else 1,
        event_risk=event_risk,
    )
    rejected = bool(abs(float(residual_error)) > float(tolerance) or not invariant_passed or str(event_risk).lower() in {"high", "runaway", "cooling_failure"})
    return {
        "residual_error": abs(float(residual_error)),
        "tolerance": float(tolerance),
        "invariant_passed": bool(invariant_passed),
        "stiffness_indicator": float(stiffness_indicator),
        "event_risk": event_risk,
        "accepted": not rejected,
        "rejected": rejected,
        "selected_solver": policy["selected_solver"],
        "solver_policy_reason": policy["solver_policy_reason"],
        "suggested_action": "" if not rejected else "reject step, reduce dt or fallback solver",
    }


def adaptive_step_control_dataframe(dynamic_result: Any | None = None, *, tolerance: float = 1.0e-6) -> pd.DataFrame:
    """Return adaptive step-control table from dynamic step acceptance."""
    steps = dynamic_step_acceptance_dataframe(dynamic_result, tolerance=tolerance)
    rows = []
    for _, row in steps.iterrows():
        rows.append(
            {
                **adaptive_step_decision(
                    float(row.get("residual_error", 0.0)),
                    tolerance=float(row.get("tolerance", tolerance)),
                    invariant_passed=bool(row.get("invariant_passed", True)),
                    event_risk=str(row.get("event_risk", "low")),
                ),
                "step_index": int(row.get("step_index", 0)),
            }
        )
    return pd.DataFrame(rows)


def adaptive_step_control_summary(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return compact adaptive step statistics."""
    df = adaptive_step_control_dataframe(dynamic_result)
    accepted = int(df["accepted"].astype(bool).sum()) if not df.empty else 0
    rejected = int(df["rejected"].astype(bool).sum()) if not df.empty else 0
    return {"passed": bool(rejected == 0 or accepted >= rejected), "accepted_steps": accepted, "rejected_steps": rejected, "rows": int(len(df))}

