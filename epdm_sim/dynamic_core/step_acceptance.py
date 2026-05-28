"""Dynamic step acceptance helpers for V6.2 solver policy."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_feedback import dynamic_residual_feedback


def dynamic_step_acceptance_record(
    step_index: int,
    residual_error: float,
    *,
    tolerance: float = 1.0e-6,
    invariant_passed: bool = True,
    event_risk: str = "low",
) -> dict[str, Any]:
    """Return one bounded step-acceptance decision."""
    err = abs(float(residual_error))
    high_event = str(event_risk).lower() in {"high", "runaway", "cooling_failure"}
    accepted = bool(np.isfinite(err) and err <= float(tolerance) and invariant_passed and not high_event)
    return {
        "step_index": int(step_index),
        "residual_error": err,
        "tolerance": float(tolerance),
        "invariant_passed": bool(invariant_passed),
        "event_risk": event_risk,
        "accepted": accepted,
        "severity": "ok" if accepted else "warning",
        "suggested_action": "" if accepted else "Reduce step size, switch solver or inspect event/residual source.",
    }


def dynamic_step_acceptance_dataframe(dynamic_result: Any | None = None, *, tolerance: float = 1.0e-6) -> pd.DataFrame:
    """Return step acceptance rows from dynamic residual feedback."""
    if dynamic_result is None:
        return pd.DataFrame([dynamic_step_acceptance_record(0, 0.0, tolerance=tolerance)])
    feedback = dynamic_residual_feedback(dynamic_result)
    rows: list[dict[str, Any]] = []
    if feedback.empty:
        rows.append(dynamic_step_acceptance_record(0, np.inf, tolerance=tolerance, invariant_passed=False))
    else:
        for idx, row in feedback.reset_index(drop=True).iterrows():
            rows.append(
                dynamic_step_acceptance_record(
                    idx,
                    float(row.get("value", 0.0) or 0.0),
                    tolerance=tolerance,
                    invariant_passed=bool(row.get("passed", True)),
                    event_risk="high" if bool(row.get("requires_solver_warning", False)) else "low",
                )
            )
    return pd.DataFrame(rows)


def dynamic_step_acceptance_summary(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return compact step acceptance statistics."""
    df = dynamic_step_acceptance_dataframe(dynamic_result)
    rate = float(df["accepted"].astype(bool).mean()) if not df.empty else 0.0
    return {
        "step_count": int(len(df)),
        "accepted_steps": int(df["accepted"].astype(bool).sum()) if not df.empty else 0,
        "step_acceptance_rate": rate,
        "passed": bool(rate >= 0.5),
    }
