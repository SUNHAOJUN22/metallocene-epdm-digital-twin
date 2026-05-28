"""Transport and heat-transfer math-core checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .heat_balance import HeatBalanceConfig, calculate_heat_balance
from .rheology import RheologyParameters, calculate_rheology


@dataclass(frozen=True)
class TransportCoreCheck:
    """One transport-core trend or bound check."""

    check_id: str
    passed: bool
    value_low: float
    value_high: float
    unit: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def pressure_drop_laminar_kPa(flow_m3_h: float, viscosity_Pa_s: float, length_m: float, diameter_m: float) -> float:
    """Return laminar Hagen-Poiseuille pressure drop proxy in kPa."""
    q_m3_s = max(float(flow_m3_h), 0.0) / 3600.0
    mu = max(float(viscosity_Pa_s), 1.0e-12)
    length = max(float(length_m), 1.0e-12)
    diameter = max(float(diameter_m), 1.0e-12)
    return 128.0 * mu * length * q_m3_s / (3.141592653589793 * diameter**4) / 1000.0


def cooling_capacity_kW(UA_W_K: float, deltaT_K: float) -> float:
    """Return positive cooling capacity in kW."""
    return max(float(UA_W_K), 0.0) * max(float(deltaT_K), 0.0) / 1000.0


def run_transport_core_checks() -> pd.DataFrame:
    """Run deterministic rheology, pressure-drop and heat-transfer trend checks."""
    params = RheologyParameters(model="carreau-yasuda")
    mu_low_solids = calculate_rheology(373.15, 8.0, 300000.0, 10.0, rheology_params=params).apparent_viscosity_Pa_s
    mu_high_solids = calculate_rheology(373.15, 18.0, 300000.0, 10.0, rheology_params=params).apparent_viscosity_Pa_s
    mu_low_t = calculate_rheology(360.0, 12.0, 300000.0, 10.0, rheology_params=params).apparent_viscosity_Pa_s
    mu_high_t = calculate_rheology(410.0, 12.0, 300000.0, 10.0, rheology_params=params).apparent_viscosity_Pa_s
    dp_big_d = pressure_drop_laminar_kPa(1.0, 0.01, 10.0, 0.05)
    dp_small_d = pressure_drop_laminar_kPa(1.0, 0.01, 10.0, 0.025)
    heat_low = calculate_heat_balance({"ethylene": 1.0}, 10.0, 2.0, config=HeatBalanceConfig())
    heat_high = calculate_heat_balance({"ethylene": 2.0}, 10.0, 2.0, config=HeatBalanceConfig())
    rows = [
        TransportCoreCheck("solids_increase_viscosity", mu_high_solids >= mu_low_solids, mu_low_solids, mu_high_solids, "Pa.s", "solids increase should not lower viscosity"),
        TransportCoreCheck("temperature_increase_lowers_viscosity", mu_high_t <= mu_low_t, mu_low_t, mu_high_t, "Pa.s", "temperature increase should not raise viscosity"),
        TransportCoreCheck("diameter_decrease_increases_dp", dp_small_d >= dp_big_d, dp_big_d, dp_small_d, "kPa", "pipe diameter decrease should increase pressure drop"),
        TransportCoreCheck("conversion_increases_heat", heat_high.Q_rxn_kW >= heat_low.Q_rxn_kW, heat_low.Q_rxn_kW, heat_high.Q_rxn_kW, "kW", "more consumed monomer should increase heat release"),
        TransportCoreCheck("cooling_capacity_positive", cooling_capacity_kW(600.0, 50.0) > cooling_capacity_kW(300.0, 50.0), cooling_capacity_kW(300.0, 50.0), cooling_capacity_kW(600.0, 50.0), "kW", "UA increase should increase cooling capacity"),
    ]
    return pd.DataFrame([row.as_dict() for row in rows])


def transport_physical_constraints_dataframe() -> pd.DataFrame:
    """Return V5.3 transport physical-constraint gate results."""
    df = run_transport_core_checks()
    df["constraint_type"] = "transport_physical_constraint"
    return df
