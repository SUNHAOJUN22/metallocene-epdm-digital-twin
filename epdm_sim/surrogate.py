"""Physical-constraint surrogate models for fast process screening."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import hashlib
import json

import numpy as np
import pandas as pd


@dataclass
class SurrogateModel:
    """Small local surrogate with explicit validity and physics metadata."""

    target: str
    features: list[str]
    model_type: str
    coefficients: list[float]
    intercept: float
    training_data_hash: str
    validity_range: dict[str, tuple[float, float]]
    metrics: dict[str, float]
    physical_constraints: list[str] = field(default_factory=list)

    def as_dataframe(self) -> pd.DataFrame:
        rows = [{"target": self.target, "model_type": self.model_type, "intercept": self.intercept, "training_data_hash": self.training_data_hash, **self.metrics}]
        for feature, coef in zip(self.features, self.coefficients):
            rows[0][f"coef_{feature}"] = coef
        return pd.DataFrame(rows)


def _hash_df(df: pd.DataFrame) -> str:
    payload = df.to_json(orient="split", default_handler=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def train_surrogate_from_sensitivity_results(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    *,
    model_type: str = "ridge",
    ridge_alpha: float = 1.0e-6,
) -> SurrogateModel:
    """Train a finite linear/ridge surrogate from sensitivity results."""
    if target not in df.columns:
        raise ValueError(f"target {target} missing from training data")
    features = features or [col for col in df.columns if col != target and pd.api.types.is_numeric_dtype(df[col])]
    clean = df[[*features, target]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(clean) < max(2, len(features)):
        raise ValueError("not enough finite training rows for surrogate")
    X = clean[features].to_numpy(dtype=float)
    y = clean[target].to_numpy(dtype=float)
    x_mean = X.mean(axis=0)
    x_std = np.where(X.std(axis=0) <= 1.0e-12, 1.0, X.std(axis=0))
    Xs = (X - x_mean) / x_std
    A = Xs.T @ Xs + ridge_alpha * np.eye(Xs.shape[1])
    coef_scaled = np.linalg.solve(A, Xs.T @ y)
    coef = coef_scaled / x_std
    intercept = float(y.mean() - np.dot(coef, x_mean))
    constraints = ["finite_bounded"]
    if target in {"Mw", "Mooney"}:
        constraints.append("hydrogen_nonincreasing")
    if target in {"viscosity", "dynamic_viscosity_Pa_s", "fouling_index"}:
        constraints.extend(["solids_nondecreasing", "temperature_nonincreasing"])
    if target in {"heat_duty", "heat_duty_kW"}:
        constraints.append("conversion_nondecreasing")
    # Enforce simple sign constraints at the local linear layer.  This keeps the
    # fast surrogate usable for screening without allowing clearly unphysical
    # monotonic directions caused by sparse/collinear DOE data.
    for i, feature in enumerate(features):
        key = feature.lower()
        if "hydrogen_nonincreasing" in constraints and ("hydrogen" in key or key in {"h2", "hydrogen_g_h"}):
            coef[i] = min(coef[i], 0.0)
        if "solids_nondecreasing" in constraints and "solid" in key:
            coef[i] = max(coef[i], 0.0)
        if "temperature_nonincreasing" in constraints and ("temperature" in key or feature == "T_C"):
            coef[i] = min(coef[i], 0.0)
        if "conversion_nondecreasing" in constraints and "conversion" in key:
            coef[i] = max(coef[i], 0.0)
    intercept = float(y.mean() - np.dot(coef, x_mean))
    pred = intercept + X @ coef
    rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
    r2 = float(1.0 - np.sum((pred - y) ** 2) / max(np.sum((y - y.mean()) ** 2), 1.0e-12))
    validity = {feature: (float(clean[feature].min()), float(clean[feature].max())) for feature in features}
    return SurrogateModel(target, features, model_type, [float(c) for c in coef], intercept, _hash_df(clean), validity, {"rmse": rmse, "r2": r2}, constraints)


def predict_with_surrogate(model: SurrogateModel, payload: dict[str, float] | pd.DataFrame) -> np.ndarray:
    """Predict finite outputs with applicability warning handled separately."""
    if isinstance(payload, pd.DataFrame):
        X = payload[model.features].to_numpy(dtype=float)
    else:
        X = np.asarray([[float(payload.get(feature, 0.0)) for feature in model.features]], dtype=float)
    pred = model.intercept + X @ np.asarray(model.coefficients, dtype=float)
    return np.asarray(pred, dtype=float)


def surrogate_applicability_warning(model: SurrogateModel, payload: dict[str, float]) -> list[str]:
    """Return warnings for out-of-training-range inputs."""
    warnings: list[str] = []
    for feature, (low, high) in model.validity_range.items():
        value = float(payload.get(feature, low))
        if value < low or value > high:
            warnings.append(f"{feature}={value} outside training range [{low}, {high}]")
    return warnings


def validate_surrogate_physics(model: SurrogateModel) -> pd.DataFrame:
    """Check encoded monotonic physical constraints against coefficient signs."""
    rows: list[dict[str, Any]] = []
    coef = dict(zip(model.features, model.coefficients))
    def add(rule: str, passed: bool, detail: str) -> None:
        rows.append({"rule": rule, "passed": bool(passed), "detail": detail})
    add("finite_coefficients", bool(np.all(np.isfinite(model.coefficients)) and np.isfinite(model.intercept)), "coefficients/intercept finite")
    if "hydrogen_nonincreasing" in model.physical_constraints:
        h_keys = [key for key in coef if "hydrogen" in key.lower() or key.lower() in {"h2", "hydrogen_g_h"}]
        add("H2_increase_Mw_not_up", all(coef[key] <= 1.0e-9 for key in h_keys) if h_keys else True, str({key: coef[key] for key in h_keys}))
    if "solids_nondecreasing" in model.physical_constraints:
        s_keys = [key for key in coef if "solid" in key.lower()]
        add("solids_increase_viscosity_not_down", all(coef[key] >= -1.0e-9 for key in s_keys) if s_keys else True, str({key: coef[key] for key in s_keys}))
    if "temperature_nonincreasing" in model.physical_constraints:
        t_keys = [key for key in coef if "temperature" in key.lower() or key == "T_C"]
        add("T_increase_viscosity_not_up", all(coef[key] <= 1.0e-9 for key in t_keys) if t_keys else True, str({key: coef[key] for key in t_keys}))
    if "conversion_nondecreasing" in model.physical_constraints:
        c_keys = [key for key in coef if "conversion" in key.lower()]
        add("conversion_increase_heat_not_down", all(coef[key] >= -1.0e-9 for key in c_keys) if c_keys else True, str({key: coef[key] for key in c_keys}))
    return pd.DataFrame(rows)
