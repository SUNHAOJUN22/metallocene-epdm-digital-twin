"""Thermodynamic calibration helpers for Henry and flash correction factors."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .solubility import calibrate_henry_parameters, liquid_saturation_concentration_mol_L
from .utils import TINY, clamp, data_path, positive, write_json


@dataclass
class ThermoCalibrationResult:
    """Thermodynamic calibration output for report/model-audit use."""

    calibration_id: str
    fitted_params: dict[str, float]
    confidence_interval: dict[str, tuple[float, float]]
    residuals: pd.DataFrame
    validity_range: dict[str, tuple[float, float]]
    warnings: list[str] = field(default_factory=list)
    dataset_id: str = "unspecified_thermo_dataset"
    created_at: str = field(default_factory=lambda: pd.Timestamp.now(tz="UTC").isoformat())
    data_hash: str = ""

    def as_dataframe(self) -> pd.DataFrame:
        rows = []
        for key, value in self.fitted_params.items():
            lo, hi = self.confidence_interval.get(key, (value, value))
            rows.append({"parameter": key, "value": value, "ci_low": lo, "ci_high": hi, "calibration_id": self.calibration_id})
        return pd.DataFrame(rows)

    def summary(self) -> dict[str, Any]:
        metrics = thermo_calibration_metrics(self.residuals)
        return {
            "calibration_id": self.calibration_id,
            "dataset_id": self.dataset_id,
            "data_hash": self.data_hash,
            "created_at": self.created_at,
            "fitted_params": self.fitted_params,
            "validity_range": self.validity_range,
            "warnings": self.warnings,
            "n": len(self.residuals),
            **metrics,
        }


def _data_hash(data: pd.DataFrame) -> str:
    if data.empty:
        return "empty"
    return hashlib.sha256(data.sort_index(axis=1).to_csv(index=False).encode("utf-8")).hexdigest()[:16]


def thermo_calibration_metrics(residuals: pd.DataFrame) -> dict[str, float]:
    """Return MAE/RMSE/R2 for thermo calibration residuals."""
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


def save_thermo_calibration_result(
    result: ThermoCalibrationResult,
    *,
    path: str | Path | None = None,
    result_id: str | None = None,
) -> dict[str, Any]:
    """Persist a calibrated thermodynamic set without modifying defaults."""
    out_path = Path(path or data_path("thermo_calibration_results.json"))
    payload: dict[str, Any] = {"sets": {}}
    if out_path.exists():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            payload.setdefault("sets", {})
        except Exception:
            payload = {"sets": {}}
    key = result_id or f"{result.calibration_id}_{result.dataset_id}_{result.data_hash or 'nohash'}"
    payload["sets"][key] = {
        "result_id": key,
        "calibration_id": result.calibration_id,
        "dataset_id": result.dataset_id,
        "fitted_params": result.fitted_params,
        "confidence_interval": {name: list(pair) for name, pair in result.confidence_interval.items()},
        "metrics": result.summary(),
        "validity_range": {name: list(pair) for name, pair in result.validity_range.items()},
        "warnings": result.warnings,
        "created_at": result.created_at,
        "data_hash": result.data_hash,
        "source": "calibrated_thermo_set",
    }
    write_json(out_path, payload)
    return payload


def _range_from(df: pd.DataFrame, column: str, default: tuple[float, float]) -> tuple[float, float]:
    if column not in df or df[column].dropna().empty:
        return default
    values = df[column].astype(float)
    return float(values.min()), float(values.max())


def calibrate_henry_from_data(data: pd.DataFrame, component: str = "ethylene", solvent: str = "hexane", dataset_id: str = "henry_dataset") -> ThermoCalibrationResult:
    """Fit a Henry reference coefficient using existing solubility utility."""
    warnings: list[str] = []
    required = {"temperature_K", "partial_pressure_MPa", "C_star_mol_L"}
    if data.empty or not required.issubset(data.columns):
        warnings.append("insufficient Henry data; current default coefficient retained.")
        ref = liquid_saturation_concentration_mol_L(component, solvent, 373.15, 1.0)
        return ThermoCalibrationResult(
            f"henry_{component}_{solvent}",
            {"solubility_ref_mol_L_MPa": ref},
            {"solubility_ref_mol_L_MPa": (ref, ref)},
            pd.DataFrame(),
            {},
            warnings,
            dataset_id=dataset_id,
            data_hash=_data_hash(data),
        )
    record = calibrate_henry_parameters(data, component=component, solvent=solvent)
    predicted = [
        liquid_saturation_concentration_mol_L(component, solvent, float(row.temperature_K), float(row.partial_pressure_MPa), modifier=record.solubility_ref_mol_L_MPa / max(liquid_saturation_concentration_mol_L(component, solvent, record.T_ref_K, 1.0), TINY))
        for row in data.itertuples()
    ]
    observed = data["C_star_mol_L"].to_numpy(dtype=float)
    residual = observed - np.asarray(predicted, dtype=float)
    spread = float(np.std(residual)) if residual.size > 1 else 0.0
    value = float(clamp(record.solubility_ref_mol_L_MPa, 1.0e-8, 20.0))
    return ThermoCalibrationResult(
        f"henry_{component}_{solvent}",
        {"solubility_ref_mol_L_MPa": value},
        {"solubility_ref_mol_L_MPa": (max(value - 2.0 * spread, 0.0), value + 2.0 * spread)},
        pd.DataFrame({"observed": observed, "predicted": predicted, "residual": residual}),
        {
            "temperature_K": _range_from(data, "temperature_K", (250.0, 500.0)),
            "partial_pressure_MPa": _range_from(data, "partial_pressure_MPa", (0.0, 5.0)),
        },
        warnings,
        dataset_id=dataset_id,
        data_hash=_data_hash(data),
    )


def calibrate_flash_k_correction(data: pd.DataFrame, default_factor: float = 1.0, dataset_id: str = "flash_dataset") -> ThermoCalibrationResult:
    """Fit a scalar K-value correction from observed/predicted vapor recovery.

    Required columns: `predicted_vapor_recovery` and `observed_vapor_recovery`.
    The correction is a bounded screening factor, not a rigorous VLE fit.
    """
    warnings: list[str] = []
    required = {"predicted_vapor_recovery", "observed_vapor_recovery"}
    if data.empty or not required.issubset(data.columns):
        warnings.append("insufficient flash data; default K correction retained.")
        return ThermoCalibrationResult("flash_k_scalar", {"K_correction": default_factor}, {"K_correction": (default_factor, default_factor)}, pd.DataFrame(), {}, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
    df = data.dropna(subset=list(required)).copy()
    df = df[(df["predicted_vapor_recovery"] > 0.0) & (df["observed_vapor_recovery"] >= 0.0)]
    if df.empty:
        warnings.append("no positive predicted recovery; default K correction retained.")
        return ThermoCalibrationResult("flash_k_scalar", {"K_correction": default_factor}, {"K_correction": (default_factor, default_factor)}, pd.DataFrame(), {}, warnings, dataset_id=dataset_id, data_hash=_data_hash(data))
    ratio = np.clip(df["observed_vapor_recovery"].to_numpy(dtype=float) / np.maximum(df["predicted_vapor_recovery"].to_numpy(dtype=float), TINY), 0.1, 10.0)
    factor = float(np.median(ratio))
    predicted = df["predicted_vapor_recovery"].to_numpy(dtype=float) * factor
    observed = df["observed_vapor_recovery"].to_numpy(dtype=float)
    residual = observed - predicted
    spread = float(np.std(residual)) if residual.size > 1 else 0.0
    return ThermoCalibrationResult(
        "flash_k_scalar",
        {"K_correction": factor},
        {"K_correction": (max(factor - 2.0 * spread, 0.0), factor + 2.0 * spread)},
        pd.DataFrame({"observed": observed, "predicted": predicted, "residual": residual}),
        {"recovery_fraction": (0.0, 1.0)},
        warnings,
        dataset_id=dataset_id,
        data_hash=_data_hash(data),
    )


def thermo_calibration_score(*results: ThermoCalibrationResult) -> float:
    """Return a bounded score summarizing thermo calibration completeness."""
    if not results:
        return 35.0
    base = 40.0 + 20.0 * len(results)
    penalty = 10.0 * sum(1 for result in results if result.warnings)
    return float(clamp(base - penalty, 0.0, 100.0))
