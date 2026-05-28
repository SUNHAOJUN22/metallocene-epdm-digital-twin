"""Runtime application of calibrated property models for V6.2."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calibrated_property_models import CalibratedPropertyModel
from .heat_balance import HeatBalanceConfig, calculate_heat_balance, calculate_reaction_heat
from .property_model_bridge import bridge_property_value
from .rheology import RheologyParameters, calculate_rheology
from .solubility import liquid_saturation_concentration_mol_L


def runtime_henry_cstar(
    component: str = "ethylene",
    solvent: str = "hexane",
    temperature_K: float = 373.15,
    partial_pressure_MPa: float = 1.0,
    *,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> dict[str, Any]:
    """Return Henry Cstar with optional calibrated model applied."""
    base = liquid_saturation_concentration_mol_L(component, solvent, temperature_K, partial_pressure_MPa)
    bridge = bridge_property_value(
        base,
        parameter_type="henry",
        parameter_name="henry",
        conditions={"temperature_C": float(temperature_K) - 273.15, "pressure_MPa": float(partial_pressure_MPa)},
        models=models,
        enable_calibrated=enable_calibrated,
    )
    return {**bridge, "property": "Cstar", "component": component, "solvent": solvent, "unit": "mol/L", "base_Cstar_mol_L": base, "runtime_value": bridge["bridged_value"]}


def runtime_rheology_viscosity(
    temperature_K: float = 373.15,
    solids_wt: float = 10.0,
    Mw: float = 300000.0,
    shear_rate_s: float = 10.0,
    *,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> dict[str, Any]:
    """Return rheology viscosity with optional calibrated model applied."""
    base_result = calculate_rheology(temperature_K, solids_wt, Mw, shear_rate_s, rheology_params=RheologyParameters(model="carreau-yasuda"))
    bridge = bridge_property_value(
        base_result.apparent_viscosity_Pa_s,
        parameter_type="viscosity",
        parameter_name="viscosity",
        conditions={"temperature_C": float(temperature_K) - 273.15, "solids_wt": float(solids_wt), "shear_rate_s": float(shear_rate_s)},
        models=models,
        enable_calibrated=enable_calibrated,
    )
    return {
        **bridge,
        "property": "apparent_viscosity",
        "unit": "Pa.s",
        "base_dynamic_viscosity_Pa_s": base_result.dynamic_viscosity_Pa_s,
        "base_apparent_viscosity_Pa_s": base_result.apparent_viscosity_Pa_s,
        "runtime_value": bridge["bridged_value"],
    }


def runtime_flash_k_values(
    k_values: dict[str, float] | None = None,
    *,
    temperature_K: float = 373.15,
    pressure_MPa: float = 1.0,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> dict[str, Any]:
    """Return flash K values with an optional calibrated correction factor."""
    base_k = k_values or {"hydrogen": 50.0, "ethylene": 5.0, "propylene": 3.0, "ENB": 0.2, "polymer_EPDM": 1.0e-9}
    bridge = bridge_property_value(
        1.0,
        parameter_type="flash_k",
        parameter_name="flash_k",
        conditions={"temperature_C": float(temperature_K) - 273.15, "pressure_MPa": float(pressure_MPa)},
        models=models,
        enable_calibrated=enable_calibrated,
    )
    factor = float(bridge["bridged_value"])
    adjusted = {key: max(float(value) * factor, 0.0) for key, value in base_k.items()}
    adjusted["polymer_EPDM"] = min(adjusted.get("polymer_EPDM", 0.0), 1.0e-9)
    passed = bool(all(np.isfinite(value) and value >= 0.0 for value in adjusted.values()) and adjusted["polymer_EPDM"] <= 1.0e-9)
    return {**bridge, "property": "flash_k", "unit": "dimensionless", "runtime_value": factor, "adjusted_k_values": adjusted, "passed": passed}


def runtime_heat_release(
    mol_consumed_h: dict[str, float] | None = None,
    *,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> dict[str, Any]:
    """Return heat release with optional calibrated deltaH magnitude."""
    consumed = mol_consumed_h or {"ethylene": 100.0, "propylene": 50.0, "ENB": 5.0}
    base_heat = calculate_reaction_heat(consumed)
    base_delta_h = 95.0
    bridge = bridge_property_value(base_delta_h, parameter_type="deltaH", parameter_name="deltaH_kJ_mol", models=models, enable_calibrated=enable_calibrated)
    factor = float(bridge["bridged_value"]) / max(base_delta_h, 1.0e-12)
    runtime_heat = max(base_heat * factor, 0.0)
    hb = calculate_heat_balance(consumed, mass_holdup_kg=100.0, Cp_mix_kJ_kgK=2.2, config=HeatBalanceConfig())
    return {
        **bridge,
        "property": "heat_release",
        "unit": "kJ/h",
        "base_heat_kJ_h": base_heat,
        "base_heat_balance_kW": hb.Q_rxn_kW,
        "runtime_value": runtime_heat,
        "runtime_heat_kJ_h": runtime_heat,
        "passed": bool(np.isfinite(runtime_heat) and runtime_heat >= 0.0),
    }


def property_model_runtime_dataframe(
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> pd.DataFrame:
    """Return V6.2 runtime property-model application rows."""
    temperature_C = float((conditions or {}).get("temperature_C", 100.0))
    pressure_MPa = float((conditions or {}).get("pressure_MPa", 1.0))
    rows = [
        runtime_henry_cstar("ethylene", "hexane", temperature_C + 273.15, pressure_MPa, models=models, enable_calibrated=enable_calibrated),
        runtime_rheology_viscosity(temperature_C + 273.15, float((conditions or {}).get("solids_wt", 10.0)), 300000.0, 10.0, models=models, enable_calibrated=enable_calibrated),
        runtime_flash_k_values(temperature_K=temperature_C + 273.15, pressure_MPa=pressure_MPa, models=models, enable_calibrated=enable_calibrated),
        runtime_heat_release(models=models, enable_calibrated=enable_calibrated),
    ]
    return pd.DataFrame(rows)
