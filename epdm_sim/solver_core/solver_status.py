"""Solver status tabulation helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .fallback_policy import fallback_policy_decision


def solver_status_record(result_or_system: Any, *, solver_name: str = "unknown", solver_failed: bool = False) -> dict[str, Any]:
    """Return a compact residual-aware solver status record."""
    decision = fallback_policy_decision(result_or_system, solver_failed=solver_failed)
    return {
        "solver_name": solver_name,
        "solver_failed": bool(solver_failed),
        "fallback_recommended": bool(decision["fallback_recommended"]),
        "fallback_reason": decision["reason"],
        "residual_penalty": float(decision["residual_penalty"]),
        "critical_count": int(decision["critical_count"]),
    }


def solver_status_dataframe(result_or_system: Any, *, solver_name: str = "unknown", solver_failed: bool = False) -> pd.DataFrame:
    """Return solver status as a DataFrame."""
    return pd.DataFrame([solver_status_record(result_or_system, solver_name=solver_name, solver_failed=solver_failed)])

