"""Residual-objective helpers split from parameter-estimation workflows."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_objective import residual_objective_score


def weighted_data_residual(observed: float, predicted: float, *, sigma: float = 1.0, unit: str = "-") -> dict[str, Any]:
    """Return a unit-tagged squared data residual."""
    scale = max(abs(float(sigma)), 1.0e-12)
    residual = (float(predicted) - float(observed)) / scale
    return {"observed": float(observed), "predicted": float(predicted), "sigma": scale, "unit": unit, "weighted_residual": float(residual), "sse": float(residual * residual)}


def combined_residual_objective(data_rows: list[dict[str, Any]], result_or_system: Any, *, residual_weight: float = 1.0) -> dict[str, Any]:
    """Combine data residuals with physical residual objective."""
    data_sse = float(sum(float(row.get("sse", 0.0)) for row in data_rows))
    physical = float(residual_objective_score(result_or_system))
    objective = data_sse + float(residual_weight) * physical
    return {"data_sse": data_sse, "physical_residual_penalty": physical, "objective": objective, "finite": bool(np.isfinite(objective))}


def residual_objectives_dataframe(data_rows: list[dict[str, Any]] | None = None, result_or_system: Any | None = None) -> pd.DataFrame:
    """Return objective audit rows."""
    rows = data_rows or [weighted_data_residual(1.0, 1.0, unit="normalized")]
    objective = combined_residual_objective(rows, result_or_system) if result_or_system is not None else {"objective": float(sum(row.get("sse", 0.0) for row in rows)), "physical_residual_penalty": 0.0}
    return pd.DataFrame([{**row, **objective} for row in rows])
