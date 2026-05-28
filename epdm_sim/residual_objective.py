"""Residual-driven objective and filtering helpers for V5.4 gates."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .residual_system import (
    ResidualSystem,
    build_flowsheet_residual_system,
    critical_residuals,
    residual_system_acceptance,
    residual_system_dataframe,
)


def _coerce_residual_system(result_or_system: Any) -> ResidualSystem:
    """Return a ResidualSystem from a flowsheet result, wrapper or system."""
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    embedded = getattr(result_or_system, "residual_system", None)
    if isinstance(embedded, ResidualSystem):
        return embedded
    return build_flowsheet_residual_system(result_or_system)


def residual_objective_score(result_or_system: Any) -> float:
    """Return a nonnegative optimizer penalty from residual-system quality.

    A perfect residual score returns 0.  Critical residuals add a hard penalty
    so optimizer/DOE callers can reject physically inconsistent candidates.
    """
    system = _coerce_residual_system(result_or_system)
    critical_count = len(critical_residuals(system))
    base_penalty = max(0.0, 100.0 - float(system.overall_score))
    return base_penalty + 1000.0 * critical_count


def reject_if_critical_residual(result_or_system: Any) -> dict[str, Any]:
    """Return a compact critical-residual acceptance record."""
    system = _coerce_residual_system(result_or_system)
    acceptance = residual_system_acceptance(system)
    acceptance["residual_objective_score"] = residual_objective_score(system)
    acceptance["rejected"] = not bool(acceptance["passed"])
    return acceptance


def residual_penalty_for_optimizer(result_or_system: Any, *, weight: float = 1.0) -> float:
    """Return a weighted residual penalty suitable for optimizer objectives."""
    return max(float(weight), 0.0) * residual_objective_score(result_or_system)


def residual_filter_for_doe(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return DOE feasibility status using an attached ResidualSystem/result.

    The function is intentionally side-effect free.  It does not run a heavy
    model unless the caller explicitly supplies a flowsheet result.
    """
    payload = candidate.get("residual_system") or candidate.get("result")
    if payload is None:
        return {
            "passed": True,
            "rejected": False,
            "reason": "no residual payload supplied; caller must provide model result before final recommendation",
            "residual_objective_score": 0.0,
        }
    status = reject_if_critical_residual(payload)
    status["reason"] = "residual critical/error filter"
    return status


def residual_diagnostics_dataframe(result_or_system: Any) -> pd.DataFrame:
    """Return detailed residual diagnostics with objective columns."""
    system = _coerce_residual_system(result_or_system)
    df = residual_system_dataframe(system)
    if df.empty:
        return pd.DataFrame(
            [
                {
                    "residual_id": "none",
                    "passed": True,
                    "severity": "ok",
                    "residual_objective_score": 0.0,
                    "critical_count": 0,
                }
            ]
        )
    df["residual_objective_score"] = residual_objective_score(system)
    df["critical_count"] = len(critical_residuals(system))
    df["accepted_for_optimizer_or_doe"] = df["critical_count"].eq(0) & (float(system.overall_score) >= 70.0)
    return df

