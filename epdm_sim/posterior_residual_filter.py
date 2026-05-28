"""Residual acceptance filters for posterior and uncertainty samples."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .parameter_constraints import parameter_constraint_results_dataframe
from .residual_objective import reject_if_critical_residual, residual_objective_score


def residual_penalty_for_sample(sample: dict[str, float], result_or_residual_system: Any) -> float:
    """Return residual plus parameter-bound penalty for one posterior sample."""
    residual_penalty = residual_objective_score(result_or_residual_system)
    constraint_df = parameter_constraint_results_dataframe(sample)
    failed = int((~constraint_df["passed"].astype(bool)).sum()) if not constraint_df.empty else 0
    return float(residual_penalty + 1000.0 * failed)


def filter_posterior_samples_by_residual(samples: pd.DataFrame, result_or_residual_system: Any) -> pd.DataFrame:
    """Annotate posterior samples with residual and parameter acceptance."""
    if samples is None or samples.empty:
        return pd.DataFrame(columns=["sample_index", "accepted", "residual_penalty", "parameter_penalty"])
    residual_status = reject_if_critical_residual(result_or_residual_system)
    rows = []
    for idx, row in samples.iterrows():
        payload = {str(key): float(value) for key, value in row.to_dict().items() if np.isfinite(float(value))}
        constraints = parameter_constraint_results_dataframe(payload)
        parameter_ok = bool(constraints.empty or constraints["passed"].astype(bool).all())
        parameter_penalty = 0.0 if parameter_ok else 1000.0
        residual_ok = not bool(residual_status["rejected"])
        penalty = residual_status["residual_objective_score"] + parameter_penalty
        rows.append(
            {
                "sample_index": int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                "accepted": bool(parameter_ok and residual_ok),
                "residual_penalty": float(residual_status["residual_objective_score"]),
                "parameter_penalty": parameter_penalty,
                "total_penalty": float(penalty),
                "critical_residual_count": int(residual_status.get("critical_count", 0)),
            }
        )
    return pd.DataFrame(rows)


def residual_acceptance_rate(samples: pd.DataFrame, result_or_residual_system: Any) -> float:
    """Return posterior residual acceptance rate in [0, 1]."""
    df = filter_posterior_samples_by_residual(samples, result_or_residual_system)
    if df.empty:
        return 0.0
    return float(np.clip(df["accepted"].astype(bool).mean(), 0.0, 1.0))


def posterior_residual_filter_dataframe(samples: pd.DataFrame | None = None, result_or_residual_system: Any | None = None) -> pd.DataFrame:
    """Return report-safe posterior residual filter output."""
    if samples is None or result_or_residual_system is None:
        return pd.DataFrame([{"status": "not_run", "residual_acceptance_rate": 0.0}])
    df = filter_posterior_samples_by_residual(samples, result_or_residual_system)
    if df.empty:
        return pd.DataFrame([{"status": "empty", "residual_acceptance_rate": 0.0}])
    summary = {
        "status": "evaluated",
        "residual_acceptance_rate": residual_acceptance_rate(samples, result_or_residual_system),
        "n_samples": int(len(df)),
        "accepted_samples": int(df["accepted"].astype(bool).sum()),
    }
    return pd.concat([pd.DataFrame([summary]), df], ignore_index=True, sort=False)

