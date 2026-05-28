"""Residual acceptance policies for calibration, DOE, optimizer and posterior."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .residual_objective import residual_filter_for_doe, residual_penalty_for_optimizer, reject_if_critical_residual
from .residual_system import ResidualSystem, residual_system_acceptance


def residual_acceptance_record(result_or_system: Any, *, context: str = "generic", minimum_score: float = 70.0) -> dict[str, Any]:
    """Return a uniform residual-acceptance record."""
    system = getattr(result_or_system, "residual_system", result_or_system)
    if not isinstance(system, ResidualSystem):
        status = reject_if_critical_residual(result_or_system)
    else:
        status = residual_system_acceptance(system, minimum_score=minimum_score)
        status["residual_objective_score"] = residual_penalty_for_optimizer(system)
        status["rejected"] = not bool(status["passed"])
    status["context"] = context
    status["minimum_score"] = float(minimum_score)
    return status


def residual_acceptance_dataframe(result_or_system: Any, *, contexts: list[str] | None = None) -> pd.DataFrame:
    """Return residual acceptance rows for multiple model consumers."""
    contexts = contexts or ["calibration", "optimizer", "doe", "posterior", "uncertainty"]
    return pd.DataFrame([residual_acceptance_record(result_or_system, context=context) for context in contexts])


def calibrated_set_residual_acceptance(result_or_system: Any) -> dict[str, Any]:
    """Return whether a calibrated parameter/property set may be saved."""
    status = residual_acceptance_record(result_or_system, context="calibrated_set")
    status["can_save_calibrated_set"] = bool(status["passed"] and not status["rejected"])
    return status


def optimizer_residual_acceptance(result_or_system: Any) -> dict[str, Any]:
    """Return optimizer residual acceptance and penalty."""
    status = residual_acceptance_record(result_or_system, context="optimizer")
    status["optimizer_penalty"] = residual_penalty_for_optimizer(result_or_system)
    return status


def doe_residual_acceptance(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return DOE residual acceptance for a candidate/result payload."""
    status = residual_filter_for_doe(candidate)
    status["context"] = "doe"
    return status

