"""Model-experiment dynamic profile alignment and residual metrics."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def align_model_to_experiment(
    model_profile: pd.DataFrame,
    experiment_profile: pd.DataFrame,
    *,
    time_col: str = "time_min",
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Interpolate model columns onto experimental time points without mutating inputs."""
    exp = experiment_profile.copy()
    model = model_profile.copy()
    if time_col not in exp.columns or time_col not in model.columns:
        raise ValueError(f"Both profiles must contain {time_col}.")
    exp_time = pd.to_numeric(exp[time_col], errors="coerce").to_numpy(dtype=float)
    model_time = pd.to_numeric(model[time_col], errors="coerce").to_numpy(dtype=float)
    cols = list(columns or [col for col in exp.columns if col in model.columns and col != time_col])
    aligned = exp[[time_col]].copy()
    for col in cols:
        x = pd.to_numeric(model[col], errors="coerce").to_numpy(dtype=float)
        aligned[f"model_{col}"] = np.interp(exp_time, model_time, x)
        aligned[f"experiment_{col}"] = pd.to_numeric(exp[col], errors="coerce").to_numpy(dtype=float)
    return aligned


def calculate_profile_residuals(aligned_profile: pd.DataFrame) -> pd.DataFrame:
    """Calculate model-minus-experiment residuals for aligned profile columns."""
    out = aligned_profile.copy()
    for col in list(out.columns):
        if col.startswith("model_"):
            metric = col.replace("model_", "", 1)
            exp_col = f"experiment_{metric}"
            if exp_col in out.columns:
                out[f"residual_{metric}"] = out[col] - out[exp_col]
    return out


def profile_fit_score(residuals: pd.DataFrame) -> pd.DataFrame:
    """Return RMSE/MAE for each residual column."""
    rows: list[dict[str, float | str]] = []
    for col in residuals.columns:
        if not col.startswith("residual_"):
            continue
        values = pd.to_numeric(residuals[col], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "metric": col.replace("residual_", "", 1),
                "rmse": float(np.sqrt(np.mean(values.to_numpy(dtype=float) ** 2))),
                "mae": float(np.mean(np.abs(values.to_numpy(dtype=float)))),
                "bias": float(np.mean(values.to_numpy(dtype=float))),
                "n": int(len(values)),
            }
        )
    return pd.DataFrame(rows)
