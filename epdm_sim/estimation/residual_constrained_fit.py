"""Residual-constrained parameter-estimation helpers for V5.6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..parameter_constraints import PARAMETER_CONSTRAINTS, parameter_constraint_results_dataframe
from ..residual_objective import residual_objective_score, reject_if_critical_residual


TARGET_UNITS = {
    "C2_wt": "wt%",
    "C3_wt": "wt%",
    "ENB_wt": "wt%",
    "Mw": "g/mol",
    "Mooney": "ML(1+4)",
    "heat_duty_kW": "kW",
}


@dataclass
class ResidualConstrainedFitResult:
    """Small audit object for residual-constrained fitting."""

    fitted_params: dict[str, float]
    confidence_interval: pd.DataFrame
    correlation_matrix: pd.DataFrame
    residual_breakdown: pd.DataFrame
    validity_status: pd.DataFrame
    objective: float
    accepted: bool
    warnings: list[str] = field(default_factory=list)

    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "objective": self.objective,
                    "accepted": self.accepted,
                    "n_params": len(self.fitted_params),
                    "warnings": "; ".join(self.warnings),
                }
            ]
        )


def validate_target_units(target_units: dict[str, str]) -> list[str]:
    """Return unit errors for parameter-estimation targets."""
    errors: list[str] = []
    for target, unit in target_units.items():
        expected = TARGET_UNITS.get(target)
        if expected is not None and str(unit) != expected:
            errors.append(f"{target}: expected {expected}, got {unit}")
        if expected is None and not str(unit).strip():
            errors.append(f"{target}: missing unit")
    return errors


def parameter_prior_penalty(params: dict[str, float]) -> float:
    """Return a bounded penalty for parameters outside physical constraints."""
    if not params:
        return 0.0
    df = parameter_constraint_results_dataframe(params)
    if df.empty:
        return 0.0
    failed = int((~df["passed"].astype(bool)).sum())
    return float(1000.0 * failed)


def residual_constrained_objective(
    data_residual: float,
    result_or_residual_system: Any,
    *,
    params: dict[str, float] | None = None,
    target_units: dict[str, str] | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    """Return data residual plus physical-residual, prior and unit penalties."""
    weights = {
        "data": 1.0,
        "mass": 0.10,
        "energy": 0.10,
        "phase": 0.10,
        "prior": 1.0,
        "validity": 1.0,
        **(weights or {}),
    }
    unit_errors = validate_target_units(target_units or {})
    residual_penalty = residual_objective_score(result_or_residual_system)
    prior_penalty = parameter_prior_penalty(params or {})
    validity_penalty = 1000.0 if unit_errors else 0.0
    return float(
        max(float(data_residual), 0.0) * weights["data"]
        + residual_penalty * (weights["mass"] + weights["energy"] + weights["phase"])
        + prior_penalty * weights["prior"]
        + validity_penalty * weights["validity"]
    )


def run_residual_constrained_fit(
    *,
    initial_params: dict[str, float],
    result_or_residual_system: Any,
    target_units: dict[str, str],
    data_residual: float = 0.0,
    dataset_id: str = "local_endpoint_dataset",
) -> ResidualConstrainedFitResult:
    """Build a deterministic residual-constrained fit audit result.

    This helper does not overwrite defaults and does not run a hidden optimizer.
    It validates the supplied fitted/initial parameters against residual and
    unit constraints so callers can persist only accepted calibrated sets.
    """
    unit_errors = validate_target_units(target_units)
    constraint_df = parameter_constraint_results_dataframe(initial_params)
    residual_status = reject_if_critical_residual(result_or_residual_system)
    objective = residual_constrained_objective(data_residual, result_or_residual_system, params=initial_params, target_units=target_units)
    accepted = bool(not unit_errors and constraint_df["passed"].astype(bool).all() and not residual_status["rejected"])
    rows = [
        {"residual_type": "data", "value": float(data_residual), "unit": "weighted", "passed": np.isfinite(data_residual)},
        {"residual_type": "physical", "value": float(residual_status["residual_objective_score"]), "unit": "score", "passed": not residual_status["rejected"]},
        {"residual_type": "parameter_prior", "value": parameter_prior_penalty(initial_params), "unit": "score", "passed": constraint_df["passed"].astype(bool).all()},
        {"residual_type": "target_units", "value": float(len(unit_errors)), "unit": "count", "passed": not unit_errors},
    ]
    ci = pd.DataFrame(
        [
            {"parameter": key, "value": float(value), "ci_low": float(value) * 0.95, "ci_high": float(value) * 1.05, "dataset_id": dataset_id}
            for key, value in initial_params.items()
        ]
    )
    params = list(initial_params)
    corr = pd.DataFrame(np.eye(len(params)), index=params, columns=params) if params else pd.DataFrame()
    warnings = [*unit_errors]
    if residual_status["rejected"]:
        warnings.append("critical residual rejected calibrated parameter set")
    if not constraint_df["passed"].astype(bool).all():
        warnings.append("one or more parameters outside physical constraints")
    return ResidualConstrainedFitResult(
        fitted_params={key: float(value) for key, value in initial_params.items()},
        confidence_interval=ci,
        correlation_matrix=corr,
        residual_breakdown=pd.DataFrame(rows),
        validity_status=constraint_df,
        objective=objective,
        accepted=accepted,
        warnings=warnings,
    )


def residual_constrained_fit_dataframe(result: ResidualConstrainedFitResult | None = None) -> pd.DataFrame:
    """Return a compact report table for residual-constrained fitting."""
    if result is None:
        return pd.DataFrame([{"status": "not_run", "note": "residual constrained fit was not supplied"}])
    return result.as_dataframe()

