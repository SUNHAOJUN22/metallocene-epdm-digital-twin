"""Data residual helpers for parameter estimation."""

from __future__ import annotations

from typing import Mapping

import pandas as pd


def parameter_residual_dataframe(observed: Mapping[str, float], predicted: Mapping[str, float], units: Mapping[str, str] | None = None) -> pd.DataFrame:
    """Return observed-predicted residual rows with units."""
    units = units or {}
    rows = []
    for key, obs in observed.items():
        pred = float(predicted.get(key, 0.0))
        rows.append({"metric": key, "observed": float(obs), "predicted": pred, "residual": pred - float(obs), "unit": units.get(key, "-")})
    return pd.DataFrame(rows)

