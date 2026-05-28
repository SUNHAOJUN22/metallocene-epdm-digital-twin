"""Small residual-aware fit runner facade."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..residual_system import ResidualSystem
from .residual_constrained_fit import run_residual_constrained_fit


def run_fit_with_residual_constraints(dataset: pd.DataFrame | None = None, **kwargs: Any) -> dict[str, Any]:
    """Run the existing residual-constrained fit and expose a stable facade."""
    result_or_system = kwargs.pop("result_or_residual_system", ResidualSystem())
    payload = {
        "initial_params": {"k_h2_transfer": 1.0, "pressure_factor": 1.0},
        "result_or_residual_system": result_or_system,
        "target_units": {"Mw": "g/mol"},
        "data_residual": 0.0 if dataset is None else float(len(dataset)) * 0.0,
        **kwargs,
    }
    result = run_residual_constrained_fit(**payload)
    return {
        "status": "success" if result.accepted else "rejected",
        "accepted": bool(result.accepted),
        "objective": float(result.objective),
        "residual_breakdown": result.residual_breakdown,
        "validity_status": result.validity_status,
    }


def fit_runner_dataframe(dataset: pd.DataFrame | None = None, **kwargs: Any) -> pd.DataFrame:
    """Return one-row fit runner status."""
    return pd.DataFrame([run_fit_with_residual_constraints(dataset, **kwargs)])
