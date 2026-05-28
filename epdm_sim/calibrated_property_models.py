"""Calibrated property-model registry helpers for V5.6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json

import numpy as np
import pandas as pd

from .property_calibration import PropertyCalibrationResult, property_calibration_score
from .utils import data_path, write_json


@dataclass(frozen=True)
class CalibratedPropertyModel:
    """One saved/default property model with provenance."""

    model_id: str
    parameter_type: str
    parameters: dict[str, float]
    dataset_id: str
    data_hash: str
    validity_range: dict[str, Any]
    uncertainty: dict[str, float]
    source_type: str = "default_estimate"
    confidence_score: float = 35.0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = "; ".join(self.warnings)
        return payload


def default_property_model(model_id: str = "default_property_estimate") -> CalibratedPropertyModel:
    """Return a low-confidence default property model."""
    return CalibratedPropertyModel(
        model_id=model_id,
        parameter_type="default_estimate",
        parameters={},
        dataset_id="default",
        data_hash="default",
        validity_range={"scope": "screening estimate"},
        uncertainty={"relative_pct": 50.0},
        source_type="default_estimate",
        confidence_score=35.0,
        warnings=["default estimate; calibrate with experiment/literature/plant data"],
    )


def calibrated_model_from_property_result(result: PropertyCalibrationResult, *, source_type: str = "experiment") -> CalibratedPropertyModel:
    """Convert a property calibration result to a saveable model record."""
    score = property_calibration_score(result)
    if source_type in {"plant", "experiment", "literature"}:
        score = min(100.0, score + 10.0)
    uncertainty = {}
    for key, value in result.fitted_params.items():
        lo, hi = result.confidence_interval.get(key, (value, value))
        uncertainty[key] = float(abs(float(hi) - float(lo)) / max(abs(float(value)), 1.0e-12))
    return CalibratedPropertyModel(
        model_id=result.model_id,
        parameter_type="calibrated",
        parameters={key: float(value) for key, value in result.fitted_params.items()},
        dataset_id=result.dataset_id,
        data_hash=result.data_hash or "nohash",
        validity_range=result.validity_range,
        uncertainty=uncertainty,
        source_type=source_type,
        confidence_score=float(score),
        warnings=list(result.warnings),
    )


def save_calibrated_property_models(models: list[CalibratedPropertyModel], *, path: str | Path | None = None) -> dict[str, Any]:
    """Persist calibrated property model records without modifying defaults."""
    out_path = Path(path or data_path("calibrated_property_models.json"))
    payload = {"models": [model.as_dict() for model in models]}
    write_json(out_path, payload)
    return payload


def load_calibrated_property_models(*, path: str | Path | None = None) -> list[CalibratedPropertyModel]:
    """Load calibrated property model records."""
    in_path = Path(path or data_path("calibrated_property_models.json"))
    if not in_path.exists():
        return [default_property_model()]
    try:
        payload = json.loads(in_path.read_text(encoding="utf-8"))
    except Exception:
        return [default_property_model()]
    models = []
    for row in payload.get("models", []):
        warnings = row.get("warnings", [])
        if isinstance(warnings, str):
            warnings = [item for item in warnings.split("; ") if item]
        models.append(
            CalibratedPropertyModel(
                model_id=str(row.get("model_id", "unknown")),
                parameter_type=str(row.get("parameter_type", "calibrated")),
                parameters={key: float(value) for key, value in dict(row.get("parameters", {})).items()},
                dataset_id=str(row.get("dataset_id", "")),
                data_hash=str(row.get("data_hash", "")),
                validity_range=dict(row.get("validity_range", {})),
                uncertainty={key: float(value) for key, value in dict(row.get("uncertainty", {})).items()},
                source_type=str(row.get("source_type", "experiment")),
                confidence_score=float(row.get("confidence_score", 50.0)),
                warnings=warnings,
            )
        )
    return models or [default_property_model()]


def calibrated_property_models_dataframe(models: list[CalibratedPropertyModel] | None = None) -> pd.DataFrame:
    """Return calibrated property models as a report table."""
    models = load_calibrated_property_models() if models is None else models
    return pd.DataFrame([model.as_dict() for model in models])


def calibrated_property_model_score(models: list[CalibratedPropertyModel] | None = None) -> float:
    """Return average property-model confidence score."""
    df = calibrated_property_models_dataframe(models)
    if df.empty:
        return 35.0
    return float(np.clip(pd.to_numeric(df["confidence_score"], errors="coerce").fillna(35.0).mean(), 0.0, 100.0))


def calibrated_property_validity_check(model: CalibratedPropertyModel, conditions: dict[str, float]) -> pd.DataFrame:
    """Check supplied conditions against a calibrated model validity range."""
    rows = []
    for variable, value in conditions.items():
        rng = model.validity_range.get(variable)
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            lo, hi = float(rng[0]), float(rng[1])
            inside = lo <= float(value) <= hi
            rows.append({"model_id": model.model_id, "variable": variable, "value": value, "lower": lo, "upper": hi, "passed": inside, "severity": "ok" if inside else "warning"})
    return pd.DataFrame(rows)


def select_calibrated_property_model(
    models: list[CalibratedPropertyModel] | None = None,
    *,
    parameter_type: str,
    conditions: dict[str, float] | None = None,
) -> CalibratedPropertyModel:
    """Select the highest-confidence calibrated model valid for conditions.

    This is a read-only selector.  It does not mutate default parameter sets and
    gives the main flowsheet/thermo/rheology layers an explicit optional path to
    calibrated property models.
    """
    models = load_calibrated_property_models() if models is None else models
    candidates = [model for model in models if model.parameter_type == parameter_type or model.model_id == parameter_type]
    if not candidates:
        candidates = [model for model in models if model.parameter_type == "calibrated"]
    if not candidates:
        return default_property_model(f"default_{parameter_type}")
    conditions = conditions or {}
    valid_candidates: list[CalibratedPropertyModel] = []
    for model in candidates:
        validity = calibrated_property_validity_check(model, conditions)
        if validity.empty or validity["passed"].astype(bool).all():
            valid_candidates.append(model)
    pool = valid_candidates or candidates
    return sorted(pool, key=lambda item: item.confidence_score, reverse=True)[0]


def apply_calibrated_property_value(base_value: float, model: CalibratedPropertyModel, parameter_name: str) -> dict[str, Any]:
    """Apply a calibrated multiplier/value to a base property with diagnostics."""
    base = float(base_value)
    if parameter_name in model.parameters:
        value = float(model.parameters[parameter_name])
        mode = "direct"
    elif f"{parameter_name}_multiplier" in model.parameters:
        value = base * float(model.parameters[f"{parameter_name}_multiplier"])
        mode = "multiplier"
    else:
        value = base
        mode = "default_base"
    finite_positive = bool(np.isfinite(value) and value >= 0.0)
    return {
        "model_id": model.model_id,
        "parameter_name": parameter_name,
        "base_value": base,
        "calibrated_value": value,
        "mode": mode,
        "source_type": model.source_type,
        "confidence_score": float(model.confidence_score),
        "passed": finite_positive,
        "warning": "" if finite_positive else "calibrated property value is not finite/nonnegative",
    }


def calibrated_property_usage_dataframe(
    models: list[CalibratedPropertyModel] | None = None,
    *,
    conditions: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Return explicit usage rows for Henry, viscosity, flash-K and deltaH paths."""
    models = load_calibrated_property_models() if models is None else models
    rows = []
    for parameter_type, parameter_name, base in [
        ("henry", "henry_multiplier", 1.0),
        ("viscosity", "viscosity_multiplier", 1.0),
        ("flash_k", "flash_k_multiplier", 1.0),
        ("deltaH", "deltaH_kJ_mol", 95.0),
    ]:
        model = select_calibrated_property_model(models, parameter_type=parameter_type, conditions=conditions or {})
        row = apply_calibrated_property_value(base, model, parameter_name)
        row["parameter_type"] = parameter_type
        row["within_validity"] = calibrated_property_validity_check(model, conditions or {}).empty or calibrated_property_validity_check(model, conditions or {})["passed"].astype(bool).all()
        rows.append(row)
    return pd.DataFrame(rows)
