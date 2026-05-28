"""Dynamic residual time-series helpers for report and gates."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..dynamic_residuals import dynamic_residuals_dataframe
from .rhs_terms import rhs_terms_from_profile


def dynamic_residual_timeseries(dynamic_result: Any) -> pd.DataFrame:
    """Return residual rows with a V5.5 coupling status column."""
    df = dynamic_residuals_dataframe(dynamic_result)
    if df.empty:
        return df
    df = df.copy()
    df["rhs_coupled"] = True
    df["gate"] = "RHS-residual step coupling"
    return df


def dynamic_rhs_residual_acceptance(dynamic_result: Any) -> dict[str, Any]:
    """Return combined residual and RHS-term acceptance."""
    residual_df = dynamic_residual_timeseries(dynamic_result)
    rhs_df = rhs_terms_from_profile(dynamic_result)
    residual_ok = bool(not residual_df.empty and residual_df["passed"].astype(bool).all())
    rhs_ok = bool(not rhs_df.empty and rhs_df["passed"].astype(bool).all())
    max_residual = float(residual_df["value"].abs().max()) if not residual_df.empty and "value" in residual_df else 0.0
    return {
        "passed": bool(residual_ok and rhs_ok and np.isfinite(max_residual)),
        "residual_rows": int(len(residual_df)),
        "rhs_rows": int(len(rhs_df)),
        "max_residual": max_residual,
    }
