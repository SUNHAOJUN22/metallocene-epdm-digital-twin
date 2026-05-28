"""Fit diagnostics for residual-constrained calibration."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def fit_diagnostics_record(fit_result: dict[str, Any]) -> dict[str, Any]:
    """Return finite/bounded diagnostics for a fit result."""
    objective = float(fit_result.get("objective", 0.0))
    accepted = bool(fit_result.get("accepted", False))
    return {
        "objective": objective,
        "finite_objective": bool(np.isfinite(objective)),
        "accepted": accepted,
        "severity": "ok" if accepted and np.isfinite(objective) else "warning",
    }


def fit_diagnostics_dataframe(fit_result: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return a report-safe fit diagnostics table."""
    return pd.DataFrame([fit_diagnostics_record(fit_result or {"objective": 0.0, "accepted": True})])
