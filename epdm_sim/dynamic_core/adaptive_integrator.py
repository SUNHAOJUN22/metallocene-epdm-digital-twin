"""Adaptive integrator audit helpers for V6.4 dynamic models."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .adaptive_step_control import adaptive_step_control_dataframe
from .event_detection import dynamic_event_detection_dataframe


def integrate_with_adaptive_policy(dynamic_result: Any | None = None, *, tolerance: float = 1.0e-6) -> dict[str, Any]:
    """Return adaptive integration status without rerunning heavy dynamics."""
    steps = adaptive_step_control_dataframe(dynamic_result, tolerance=tolerance)
    events = dynamic_event_detection_dataframe(dynamic_result)
    rejected = int(steps.get("rejected", pd.Series(dtype=bool)).astype(bool).sum()) if not steps.empty else 0
    accepted = int(steps.get("accepted", pd.Series(dtype=bool)).astype(bool).sum()) if not steps.empty else 0
    high_risk = int(events.get("high_risk", pd.Series(dtype=bool)).astype(bool).sum()) if not events.empty and "high_risk" in events else 0
    return {
        "integrator": "adaptive_policy_audit",
        "accepted_steps": accepted,
        "rejected_steps": rejected,
        "event_count": int(len(events)),
        "high_risk_events": high_risk,
        "solver_policy_reason": "accepted residual/state/event checks" if rejected == 0 else "rejected step due to residual/state/event risk",
        "passed": bool(accepted >= rejected and high_risk == 0),
    }


def adaptive_integrator_dataframe(dynamic_result: Any | None = None, *, tolerance: float = 1.0e-6) -> pd.DataFrame:
    """Return adaptive integrator step rows."""
    steps = adaptive_step_control_dataframe(dynamic_result, tolerance=tolerance)
    if steps.empty:
        return pd.DataFrame([integrate_with_adaptive_policy(dynamic_result, tolerance=tolerance)])
    rows = []
    for _, row in steps.iterrows():
        rows.append(
            {
                "step_index": int(row.get("step_index", 0)),
                "accepted": bool(row.get("accepted", True)),
                "rejected": bool(row.get("rejected", False)),
                "residual_error": float(row.get("residual_error", 0.0)),
                "selected_solver": row.get("selected_solver", ""),
                "solver_policy_reason": row.get("solver_policy_reason", ""),
                "event_risk": row.get("event_risk", "low"),
                "integrator": "adaptive_policy_audit",
            }
        )
    return pd.DataFrame(rows)


def adaptive_integrator_summary(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return compact adaptive integrator status."""
    status = integrate_with_adaptive_policy(dynamic_result)
    df = adaptive_integrator_dataframe(dynamic_result)
    status["rows"] = int(len(df))
    return status


def adaptive_integrator_gate(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return release-gate status for adaptive integrator diagnostics."""
    return adaptive_integrator_summary(dynamic_result)

