"""Lightweight DAE constraint diagnostics for dynamic reactor results."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..dynamic_core.dae_constraints import dae_constraints_dataframe, dae_constraints_status


def dae_solver_status(dynamic_result: Any) -> dict[str, Any]:
    """Return DAE/fallback status from dynamic state constraints."""
    status = dae_constraints_status(dynamic_result)
    return {
        "solver_id": "dae_constraint_diagnostics",
        "dae_ready": bool(status["passed"]),
        "fallback_reason": "" if status["passed"] else "DAE state constraints failed or profile missing",
        "constraint_rows": int(status["rows"]),
        "failed": int(status["failed"]),
    }


def dae_solver_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Return DAE solver status and constraints."""
    status = dae_solver_status(dynamic_result)
    constraints = dae_constraints_dataframe(dynamic_result)
    out = constraints.copy()
    for key, value in status.items():
        out[key] = value
    return out
