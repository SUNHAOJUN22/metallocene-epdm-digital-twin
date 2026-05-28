"""Confidence interval helpers for fitted parameters."""

from __future__ import annotations

import pandas as pd


def confidence_interval_dataframe(samples: pd.DataFrame, *, alpha: float = 0.05) -> pd.DataFrame:
    """Return quantile confidence intervals for parameter samples."""
    if samples.empty:
        return pd.DataFrame(columns=["parameter", "low", "high"])
    low_q = max(min(alpha / 2.0, 0.5), 0.0)
    high_q = min(max(1.0 - alpha / 2.0, 0.5), 1.0)
    rows = []
    for col in samples.select_dtypes(include="number").columns:
        rows.append({"parameter": col, "low": float(samples[col].quantile(low_q)), "high": float(samples[col].quantile(high_q))})
    return pd.DataFrame(rows)

