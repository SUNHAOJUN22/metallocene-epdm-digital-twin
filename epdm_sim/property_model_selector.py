"""Calibrated property model selector for V6.0 flowsheet governance."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .calibrated_property_models import (
    CalibratedPropertyModel,
    apply_calibrated_property_value,
    calibrated_property_validity_check,
    default_property_model,
    load_calibrated_property_models,
    select_calibrated_property_model,
)


def property_model_selector(
    *,
    parameter_type: str,
    template_id: str = "EPDM_EPM_metallocene_solution",
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
) -> dict[str, Any]:
    """Select a property model and report confidence/validity diagnostics."""
    models = load_calibrated_property_models() if models is None else models
    model = select_calibrated_property_model(models, parameter_type=parameter_type, conditions=conditions or {})
    validity = calibrated_property_validity_check(model, conditions or {})
    within = bool(validity.empty or validity["passed"].astype(bool).all())
    if model.parameter_type == "default_estimate":
        model = default_property_model(f"default_{parameter_type}")
    return {
        "template_id": template_id,
        "parameter_type": parameter_type,
        "model_id": model.model_id,
        "source_type": model.source_type,
        "confidence_score": float(model.confidence_score),
        "within_validity": within,
        "warning": "" if within else "selected calibrated property model is outside validity range",
    }


def apply_selected_property_model(
    base_value: float,
    parameter_name: str,
    *,
    parameter_type: str,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
) -> dict[str, Any]:
    """Apply selected calibrated property parameter to a base value."""
    model = select_calibrated_property_model(models, parameter_type=parameter_type, conditions=conditions or {})
    applied = apply_calibrated_property_value(base_value, model, parameter_name)
    selected = property_model_selector(parameter_type=parameter_type, conditions=conditions, models=models)
    return {**selected, **applied}


def property_model_selection_dataframe(
    *,
    template_id: str = "EPDM_EPM_metallocene_solution",
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
) -> pd.DataFrame:
    """Return property selector rows for Henry, viscosity, flash-K and deltaH."""
    rows = [
        property_model_selector(parameter_type=ptype, template_id=template_id, conditions=conditions, models=models)
        for ptype in ["henry", "viscosity", "flash_k", "deltaH"]
    ]
    return pd.DataFrame(rows)
