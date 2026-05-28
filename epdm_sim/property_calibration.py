"""R&D property calibration utilities for viscosity and heat-release inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .rheology import RheologyParameters, zero_shear_solution_viscosity
from .utils import R_GAS, TINY, clamp, data_path, positive, write_json


@dataclass
class PropertyCalibrationResult:
    """Calibration result with finite diagnostics and audit metadata."""

    model_id: str
    fitted_params: dict[str, float]
    confidence_interval: dict[str, tuple[float, float]]
    residuals: pd.DataFrame
    validity_range: dict[str, tuple[float, float]]
    warnings: list[str] = field(default_factory=list)
    dataset_id: str = "unspecified_property_dataset"
    created_at: str = field(default_factory=lambda: pd.Timestamp.now(tz="UTC").isoformat())
    data_hash: str = ""

    def as_dataframe(self) -> pd.DataFrame:
        rows = []
        for name, value in self.fitted_params.items():
            lo, hi = self.confidence_interval.get(name, (value, value))
            rows.append({"parameter": name, "value": value, "ci_low": lo, "ci_high": hi, "model_id": self.model_id})
        return pd.DataFrame(rows)

    def summary(self) -> dict[str, Any]:
        metrics = calibration_metrics(self.residuals)
        return {
            "model_id": self.model_id,
            "dataset_id": self.dataset_id,
            "data_hash": self.data_hash,
            "created_at": self.created_at,
            "warnings": "; ".join(self.warnings),
            **metrics,
        }


def _data_hash(data: pd.DataFrame) -> str:
    if data.empty:
        return "empty"
    payload = data.sort_index(axis=1).to_csv(index=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def calibration_metrics(residuals: pd.DataFrame) -> dict[str, float]:
    """Return MAE/RMSE/R2 metrics for calibration residuals."""
    if residuals.empty or not {"observed", "predicted", "residual"}.issubset(residuals.columns):
        return {"MAE": 0.0, "RMSE": 0.0, "R2": 0.0}
    observed = residuals["observed"].to_numpy(dtype=float)
    predicted = residuals["predicted"].to_numpy(dtype=float)
    residual = residuals["residual"].to_numpy(dtype=float)
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    ss_res = float(np.sum(np.square(observed - predicted)))
    ss_tot = float(np.sum(np.square(observed - np.mean(observed))))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > TINY else 1.0
    return {"MAE": mae, "RMSE": rmse, "R2": float(np.clip(r2, -1.0, 1.0))}


def save_property_calibration_result(
    result: PropertyCalibrationResult,
    *,
    path: str | Path | None = None,
    result_id: str | None = None,
) -> dict[str, Any]:
    """Persist a calibrated property set without modifying defaults."""
    out_path = Path(path or data_path("property_calibration_results.json"))
    payload: dict[str, Any] = {"sets": {}}
    if out_path.exists():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            payload.setdefault("sets", {})
        except Exception:
            payload = {"sets": {}}
    key = result_id or f"{result.model_id}_{result.dataset_id}_{result.data_hash or 'nohash'}"
    payload["sets"][key] = {
        "result_id": key,
        "model_id": result.model_id,
        "dataset_id": result.dataset_id,
        "fitted_params": result.fitted_params,
        "confidence_interval": {name: list(pair) for name, pair in result.confidence_interval.items()},
        "metrics": result.summary(),
        "validity_range": {name: list(pair) for name, pair in result.validity_range.items()},
        "warnings": result.warnings,
        "created_at": result.created_at,
        "data_hash": result.data_hash,
        "source": "calibrated_property_set",
    }
    write_json(out_path, payload)
    return payload


def property_calibration_score(*results: PropertyCalibrationResult) -> float:
    """Return a bounded completeness/quality score for property calibration."""
    if not results:
        return 35.0
    score = 45.0 + 15.0 * len(results)
    for result in results:
        metrics = result.summary()
        score += max(0.0, 10.0 * float(metrics.get("R2", 0.0)))
        if result.warnings:
            score -= 10.0
    return float(clamp(score, 0.0, 100.0))


def _range_from(df: pd.DataFrame, column: str, default: tuple[float, float]) -> tuple[float, float]:
    if column not in df or df[column].dropna().empty:
        return default
    values = df[column].astype(float)
    return float(values.min()), float(values.max())


def calibrate_viscosity_model(data: pd.DataFrame, defaults: RheologyParameters | None = None, dataset_id: str = "viscosity_dataset") -> PropertyCalibrationResult:
    """Fit EPDM apparent viscosity parameters from rheology observations.

    Required columns: `temperature_K`, `solids_wt`, `Mw`, `viscosity_Pa_s`.
    The fitted model is the same log-linear structure used by the R&D
    solution-viscosity model, so units remain Pa.s, wt%, K and g/mol.
    """
    p = defaults or RheologyParameters()
    needed = {"temperature_K", "solids_wt", "Mw", "viscosity_Pa_s"}
    warnings: list[str] = []
    if data.empty or not needed.issubset(data.columns):
        warnings.append("insufficient viscosity calibration data; default rheology parameters retained.")
        residuals = pd.DataFrame(columns=["observed", "predicted", "residual"])
        params = {"A_mu": p.A_mu, "B_mu": p.B_mu, "alpha_Mw": p.alpha_Mw}
        ci = {key: (value, value) for key, value in params.items()}
        return PropertyCalibrationResult("viscosity_loglinear", params, ci, residuals, {}, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
    df = data.dropna(subset=list(needed)).copy()
    df = df[(df["temperature_K"] > 0.0) & (df["Mw"] > 0.0) & (df["viscosity_Pa_s"] > 0.0)]
    if len(df) < 3:
        warnings.append("fewer than three valid viscosity points; default rheology parameters retained.")
        residuals = pd.DataFrame(columns=["observed", "predicted", "residual"])
        params = {"A_mu": p.A_mu, "B_mu": p.B_mu, "alpha_Mw": p.alpha_Mw}
        ci = {key: (value, value) for key, value in params.items()}
        return PropertyCalibrationResult("viscosity_loglinear", params, ci, residuals, {}, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
    solids = np.clip(df["solids_wt"].to_numpy(dtype=float) / 100.0, 0.0, 0.75)
    mw_term = np.log(np.maximum(df["Mw"].to_numpy(dtype=float), 1.0) / 300000.0)
    T = np.maximum(df["temperature_K"].to_numpy(dtype=float), 1.0)
    base_mu = p.mu_solvent_ref_Pa_s * np.exp(np.clip(p.E_mu_J_mol / R_GAS * (1.0 / T - 1.0 / p.T_ref_K), -40.0, 40.0))
    y = np.log(df["viscosity_Pa_s"].to_numpy(dtype=float) / np.maximum(base_mu, TINY))
    X = np.column_stack([solids, solids**2, mw_term])
    coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
    coeffs = np.nan_to_num(coeffs, nan=0.0, posinf=0.0, neginf=0.0)
    params = {
        "A_mu": float(clamp(coeffs[0], 0.0, 50.0)),
        "B_mu": float(clamp(coeffs[1], 0.0, 100.0)),
        "alpha_Mw": float(clamp(coeffs[2], 0.0, 3.0)),
    }
    fitted = RheologyParameters(A_mu=params["A_mu"], B_mu=params["B_mu"], alpha_Mw=params["alpha_Mw"])
    predicted = np.array([zero_shear_solution_viscosity(row.temperature_K, row.solids_wt, row.Mw, fitted) for row in df.itertuples()], dtype=float)
    observed = df["viscosity_Pa_s"].to_numpy(dtype=float)
    residual = observed - predicted
    spread = float(np.std(residual)) if residual.size > 1 else 0.0
    ci = {
        key: (float(max(value - 2.0 * spread, 0.0)), float(value + 2.0 * spread))
        for key, value in params.items()
    }
    residuals = pd.DataFrame({"observed": observed, "predicted": predicted, "residual": residual})
    validity = {
        "temperature_K": _range_from(df, "temperature_K", (250.0, 500.0)),
        "solids_wt": _range_from(df, "solids_wt", (0.0, 40.0)),
        "Mw": _range_from(df, "Mw", (50000.0, 1000000.0)),
    }
    return PropertyCalibrationResult("viscosity_loglinear", params, ci, residuals, validity, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))


def calibrate_heat_release(data: pd.DataFrame, default_deltaH_kJ_mol: float = -90.0, dataset_id: str = "calorimetry_dataset") -> PropertyCalibrationResult:
    """Fit an apparent heat of polymerization from calorimetry data.

    Required columns: `consumed_mol` and `Q_rxn_kJ`.  The fitted sign follows
    chemistry convention: exothermic polymerization has negative deltaH.
    """
    warnings: list[str] = []
    if data.empty or not {"consumed_mol", "Q_rxn_kJ"}.issubset(data.columns):
        warnings.append("insufficient calorimetry data; default deltaH retained.")
        params = {"deltaH_kJ_mol": float(default_deltaH_kJ_mol)}
        return PropertyCalibrationResult("heat_release_linear", params, {"deltaH_kJ_mol": (default_deltaH_kJ_mol, default_deltaH_kJ_mol)}, pd.DataFrame(), {}, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
    df = data.dropna(subset=["consumed_mol", "Q_rxn_kJ"]).copy()
    df = df[(df["consumed_mol"] > 0.0) & np.isfinite(df["Q_rxn_kJ"])]
    if df.empty:
        warnings.append("no positive consumed_mol values; default deltaH retained.")
        params = {"deltaH_kJ_mol": float(default_deltaH_kJ_mol)}
        return PropertyCalibrationResult("heat_release_linear", params, {"deltaH_kJ_mol": (default_deltaH_kJ_mol, default_deltaH_kJ_mol)}, pd.DataFrame(), {}, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
    slope = float(np.sum(df["consumed_mol"] * df["Q_rxn_kJ"]) / max(np.sum(df["consumed_mol"] ** 2), TINY))
    deltaH = -abs(slope)
    predicted = abs(deltaH) * df["consumed_mol"].to_numpy(dtype=float)
    residual = df["Q_rxn_kJ"].to_numpy(dtype=float) - predicted
    spread = float(np.std(residual)) if len(residual) > 1 else 0.0
    params = {"deltaH_kJ_mol": deltaH}
    ci = {"deltaH_kJ_mol": (deltaH - 2.0 * spread, deltaH + 2.0 * spread)}
    residuals = pd.DataFrame({"observed": df["Q_rxn_kJ"], "predicted": predicted, "residual": residual})
    validity = {"consumed_mol": _range_from(df, "consumed_mol", (0.0, 1.0))}
    return PropertyCalibrationResult("heat_release_linear", params, ci, residuals, validity, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
