"""Numerical stability checks for dynamic reactor profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DynamicStabilityResult:
    """One dynamic profile stability check."""

    check_id: str
    passed: bool
    severity: str
    message: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        row = self.__dict__.copy()
        row["details"] = str(self.details)
        return row


def dynamic_stability_dataframe(results: list[DynamicStabilityResult]) -> pd.DataFrame:
    """Return dynamic stability checks as a DataFrame."""
    return pd.DataFrame([item.as_dict() for item in results])


def check_dynamic_stability(profile: pd.DataFrame) -> list[DynamicStabilityResult]:
    """Run non-negativity, boundedness and trend checks on an ODE profile."""
    checks: list[DynamicStabilityResult] = []
    nonnegative_cols = [col for col in ["C_E_mol_L", "C_P_mol_L", "C_ENB_mol_L", "C_H2_mol_L", "solids_wt", "viscosity_Pa_s", "Mw", "Mooney", "catalyst_active"] if col in profile]
    min_values = {col: float(profile[col].min()) for col in nonnegative_cols}
    checks.append(DynamicStabilityResult("nonnegative_states", all(value >= -1.0e-9 for value in min_values.values()), "error", "Dynamic states remain nonnegative.", min_values))
    temp_min = float(profile["T_C"].min()) if "T_C" in profile else 25.0
    temp_max = float(profile["T_C"].max()) if "T_C" in profile else 25.0
    checks.append(DynamicStabilityResult("temperature_bounds", temp_min > -273.15 and temp_max < 260.0, "warning", "Temperature remains within screening bounds.", {"min_C": temp_min, "max_C": temp_max}))
    if "solids_wt" in profile:
        monotonic = bool((profile["solids_wt"].diff().fillna(0.0) >= -1.0e-6).all())
        checks.append(DynamicStabilityResult("polymer_mass_non_decreasing", monotonic, "warning", "Solids/polymer mass is nondecreasing over time.", {"initial": float(profile["solids_wt"].iloc[0]), "final": float(profile["solids_wt"].iloc[-1])}))
    if {"Q_rxn_kW", "catalyst_active"}.issubset(profile.columns):
        low_cat = profile[profile["catalyst_active"] < 1.0e-3]
        quenched_rate_ok = True if low_cat.empty else float(low_cat["Q_rxn_kW"].max()) <= max(float(profile["Q_rxn_kW"].max()) * 0.05, 1.0e-6)
        checks.append(DynamicStabilityResult("quench_or_deactivation_reduces_heat", quenched_rate_ok, "warning", "Catalyst deactivation/quench reduces heat generation.", {"low_cat_rows": len(low_cat)}))
    finite = bool(profile.replace([float("inf"), -float("inf")], pd.NA).notna().all().all())
    checks.append(DynamicStabilityResult("profile_finite", finite, "error", "Dynamic profile contains finite values.", {"rows": len(profile)}))
    return checks
