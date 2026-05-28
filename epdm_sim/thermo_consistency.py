"""Thermodynamic sanity and phase-split consistency checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .eos import cubic_eos_details, k_value_comparison
from .flash import Flash
from .flowsheet import load_default_config, run_flowsheet
from .solubility import liquid_saturation_concentration_mol_L
from .utils import c_to_k, mpa_to_pa


@dataclass(frozen=True)
class ThermoConsistencyResult:
    """One thermo consistency check."""

    check_id: str
    passed: bool
    severity: str
    message: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        row = self.__dict__.copy()
        row["details"] = str(self.details)
        return row


def thermo_consistency_dataframe(results: list[ThermoConsistencyResult]) -> pd.DataFrame:
    """Return thermo consistency checks as a DataFrame."""
    return pd.DataFrame([item.as_dict() for item in results])


def run_thermo_consistency_checks() -> list[ThermoConsistencyResult]:
    """Run default EOS, Henry and flash trend checks."""
    checks: list[ThermoConsistencyResult] = []
    names = ["hydrogen", "ethylene", "propylene", "ENB", "hexane", "polymer_pseudo"]
    comparison = k_value_comparison(names[:-1], c_to_k(100.0), mpa_to_pa(1.0))
    checks.append(
        ThermoConsistencyResult(
            "k_values_positive",
            all(value > 0.0 for row in comparison.values() for value in row.values()),
            "error",
            "Wilson/PR/SRK K values are positive.",
            comparison,
        )
    )
    eos_details = {name: cubic_eos_details(name, c_to_k(100.0), mpa_to_pa(1.0), "PR") for name in names}
    checks.append(
        ThermoConsistencyResult(
            "eos_roots_phi_finite_positive",
            all(float(item["Z_vapor"]) > 0.0 and float(item["phi_v"]) > 0.0 and float(item["K"]) > 0.0 for item in eos_details.values()),
            "error",
            "EOS Z roots, phi and K are finite positive; polymer is nonvolatile.",
            eos_details,
        )
    )
    c_low = liquid_saturation_concentration_mol_L("ethylene", "hexane", c_to_k(100.0), 0.2)
    c_high = liquid_saturation_concentration_mol_L("ethylene", "hexane", c_to_k(100.0), 1.0)
    checks.append(ThermoConsistencyResult("henry_pressure_monotonic", c_high >= c_low >= 0.0, "error", "Henry Cstar increases with pressure and remains nonnegative.", {"low": c_low, "high": c_high}))
    result = run_flowsheet(load_default_config())
    inlet = result.streams["Quenched solution"]
    high_p = Flash("thermo-high").calculate(inlet, c_to_k(100.0), mpa_to_pa(0.5))
    low_p = Flash("thermo-low").calculate(inlet, c_to_k(100.0), mpa_to_pa(0.05))
    hot = Flash("thermo-hot").calculate(inlet, c_to_k(140.0), mpa_to_pa(0.2))
    cool = Flash("thermo-cool").calculate(inlet, c_to_k(80.0), mpa_to_pa(0.2))
    checks.append(ThermoConsistencyResult("flash_pressure_trend", low_p.vapor_fraction >= high_p.vapor_fraction, "warning", "Lower flash pressure increases or preserves vapor fraction.", {"highP": high_p.vapor_fraction, "lowP": low_p.vapor_fraction}))
    light_hot = hot.vapor.mass_flows.get("hydrogen", 0.0) + hot.vapor.mass_flows.get("ethylene", 0.0) + hot.vapor.mass_flows.get("propylene", 0.0)
    light_cool = cool.vapor.mass_flows.get("hydrogen", 0.0) + cool.vapor.mass_flows.get("ethylene", 0.0) + cool.vapor.mass_flows.get("propylene", 0.0)
    checks.append(ThermoConsistencyResult("flash_temperature_light_recovery", light_hot >= light_cool, "warning", "Higher flash temperature increases light-component vapor recovery.", {"cool": light_cool, "hot": light_hot}))
    checks.append(ThermoConsistencyResult("polymer_nonvolatile", high_p.vapor.polymer_mass_kg_h == 0.0 and low_p.vapor.polymer_mass_kg_h == 0.0, "error", "Polymer pseudo-component remains out of vapor phase.", {"highP_polymer": high_p.vapor.polymer_mass_kg_h, "lowP_polymer": low_p.vapor.polymer_mass_kg_h}))
    return checks


def thermo_physical_constraints_dataframe() -> pd.DataFrame:
    """Return V5.3 thermodynamic physical-constraint checks."""
    df = thermo_consistency_dataframe(run_thermo_consistency_checks())
    df["constraint_type"] = "thermo_physical_constraint"
    return df
