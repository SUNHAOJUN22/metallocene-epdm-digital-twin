"""Bridge calibrated property-model selection into calculation paths."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calibrated_property_models import CalibratedPropertyModel, apply_calibrated_property_value, calibrated_property_validity_check, select_calibrated_property_model
from .property_model_selector import property_model_selector


def bridge_property_value(
    base_value: float,
    *,
    parameter_type: str,
    parameter_name: str,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> dict[str, Any]:
    """Return a property value with explicit default/calibrated provenance."""
    base = float(base_value)
    if not enable_calibrated:
        return {
            "parameter_type": parameter_type,
            "parameter_name": parameter_name,
            "base_value": base,
            "bridged_value": base,
            "model_id": f"default_{parameter_type}",
            "source_type": "default_estimate",
            "confidence_score": 35.0,
            "within_validity": True,
            "mode": "default_disabled",
            "warning": "calibrated property bridge disabled",
            "passed": bool(np.isfinite(base) and base >= 0.0),
        }
    model = select_calibrated_property_model(models, parameter_type=parameter_type, conditions=conditions or {})
    validity = calibrated_property_validity_check(model, conditions or {})
    within = bool(validity.empty or validity["passed"].astype(bool).all())
    applied = apply_calibrated_property_value(base, model, parameter_name)
    value = float(applied["calibrated_value"]) if within else base
    warning = applied.get("warning", "")
    if not within:
        warning = "selected calibrated property model outside validity range; default value used"
    return {
        "parameter_type": parameter_type,
        "parameter_name": parameter_name,
        "base_value": base,
        "bridged_value": value,
        "model_id": model.model_id,
        "source_type": model.source_type,
        "confidence_score": float(model.confidence_score if within else min(model.confidence_score, 35.0)),
        "within_validity": within,
        "mode": applied.get("mode", "default_base") if within else "validity_fallback",
        "warning": warning,
        "passed": bool(np.isfinite(value) and value >= 0.0),
    }


def property_model_bridge_dataframe(
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
) -> pd.DataFrame:
    """Return V6.1 bridge rows for Henry, viscosity, flash-K and deltaH."""
    rows = [
        bridge_property_value(1.0, parameter_type="henry", parameter_name="henry", conditions=conditions, models=models),
        bridge_property_value(1.0, parameter_type="viscosity", parameter_name="viscosity", conditions=conditions, models=models),
        bridge_property_value(1.0, parameter_type="flash_k", parameter_name="flash_k", conditions=conditions, models=models),
        bridge_property_value(95.0, parameter_type="deltaH", parameter_name="deltaH_kJ_mol", conditions=conditions, models=models),
    ]
    return pd.DataFrame(rows)


def property_bridge_confidence_adjustment(
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
) -> dict[str, Any]:
    """Return confidence adjustment from selected property-model bridge rows."""
    df = property_model_bridge_dataframe(conditions=conditions, models=models)
    selector = property_model_selector(parameter_type="viscosity", conditions=conditions or {}, models=models)
    confidence = float(pd.to_numeric(df["confidence_score"], errors="coerce").fillna(35.0).mean())
    warnings = [str(item) for item in df["warning"].fillna("") if str(item)]
    return {
        "property_bridge_confidence": confidence,
        "selector_reference_model": selector["model_id"],
        "warnings": "; ".join(warnings),
        "passed": bool(df["passed"].astype(bool).all() and confidence >= 0.0),
    }
