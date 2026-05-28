"""Simple dimensional and unit-conversion checks used by V4.6 reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .equation_registry import load_equation_registry
from .utils import kg_h_to_mol_h, safe_divide


@dataclass(frozen=True)
class DimensionalCheckResult:
    """One unit/quantity consistency check."""

    check_id: str
    passed: bool
    severity: str
    message: str
    value: float | str = ""
    expected: str = ""

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def kj_h_to_kw(value_kJ_h: float) -> float:
    """Convert kJ/h to kW."""
    return float(value_kJ_h) / 3600.0


def mol_L_to_mol_m3(value_mol_L: float) -> float:
    """Convert mol/L to mol/m3."""
    return float(value_mol_L) * 1000.0


def mpa_pa_consistency(pressure_MPa: float, pressure_Pa: float, tol: float = 1.0e-9) -> bool:
    """Check MPa and Pa representations of pressure."""
    return abs(float(pressure_MPa) * 1.0e6 - float(pressure_Pa)) <= max(abs(pressure_Pa), 1.0) * tol


def wt_fraction_consistency(wt_percent: float, fraction: float, tol: float = 1.0e-9) -> bool:
    """Check wt% and fraction representations."""
    return abs(float(wt_percent) / 100.0 - float(fraction)) <= tol


def run_dimensional_checks(sample: dict[str, float] | None = None) -> list[DimensionalCheckResult]:
    """Run representative unit-conversion checks with optional sample overrides."""
    sample = sample or {}
    results = [
        DimensionalCheckResult("kJ_h_to_kW", abs(kj_h_to_kw(sample.get("Q_kJ_h", 3600.0)) - sample.get("Q_kW", 1.0)) < 1.0e-9, "ok", "kJ/h to kW conversion", kj_h_to_kw(sample.get("Q_kJ_h", 3600.0)), "1 kW for 3600 kJ/h"),
        DimensionalCheckResult("kg_h_to_mol_h", np.isfinite(kg_h_to_mol_h(sample.get("mass_kg_h", 28.054), sample.get("MW_g_mol", 28.054))), "ok", "kg/h to mol/h finite", kg_h_to_mol_h(sample.get("mass_kg_h", 28.054), sample.get("MW_g_mol", 28.054)), "finite positive"),
        DimensionalCheckResult("Pa_vs_MPa", mpa_pa_consistency(sample.get("pressure_MPa", 1.0), sample.get("pressure_Pa", 1.0e6)), "ok", "MPa and Pa pressure consistency", sample.get("pressure_Pa", 1.0e6), "1 MPa = 1e6 Pa"),
        DimensionalCheckResult("wt_percent_fraction", wt_fraction_consistency(sample.get("wt_percent", 10.0), sample.get("fraction", 0.10)), "ok", "wt% and fraction consistency", sample.get("wt_percent", 10.0), "10 wt% = 0.10"),
        DimensionalCheckResult("mol_L_to_mol_m3", abs(mol_L_to_mol_m3(sample.get("C_mol_L", 1.0)) - sample.get("C_mol_m3", 1000.0)) < 1.0e-9, "ok", "mol/L to mol/m3 conversion", mol_L_to_mol_m3(sample.get("C_mol_L", 1.0)), "1 mol/L = 1000 mol/m3"),
    ]
    registry_warnings = []
    for equation in load_equation_registry().values():
        if not equation.output_unit or not equation.variable_units:
            registry_warnings.append(equation.equation_id)
    results.append(DimensionalCheckResult("equation_registry_units", not registry_warnings, "ok" if not registry_warnings else "error", "all equations have output and variable units", ", ".join(registry_warnings), "no missing unit metadata"))
    return results


def dimensional_checks_dataframe(results: list[DimensionalCheckResult] | None = None) -> pd.DataFrame:
    """Return dimensional checks as a DataFrame."""
    results = run_dimensional_checks() if results is None else results
    return pd.DataFrame([item.as_dict() for item in results])
