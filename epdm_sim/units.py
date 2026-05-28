"""Unit conversion and dimensional sanity checks.

This module deliberately avoids a heavy unit package.  It provides the small
set of conversions and assertions used repeatedly by the process, reactor,
flash, heat-balance and transport models.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .utils import TINY, safe_divide


def kg_h_to_mol_h(mass_kg_h: float, mw_g_mol: float) -> float:
    """Convert kg/h to mol/h."""
    return float(mass_kg_h) * 1000.0 / max(float(mw_g_mol), TINY)


def mol_h_to_kg_h(mol_h: float, mw_g_mol: float) -> float:
    """Convert mol/h to kg/h."""
    return float(mol_h) * float(mw_g_mol) / 1000.0


def mol_L_to_mol_m3(value: float) -> float:
    """Convert mol/L to mol/m3."""
    return float(value) * 1000.0


def mol_m3_to_mol_L(value: float) -> float:
    """Convert mol/m3 to mol/L."""
    return float(value) / 1000.0


def mpa_to_pa(value: float) -> float:
    """Convert MPa to Pa."""
    return float(value) * 1.0e6


def pa_to_mpa(value: float) -> float:
    """Convert Pa to MPa."""
    return float(value) / 1.0e6


def c_to_k(value: float) -> float:
    """Convert Celsius to Kelvin."""
    return float(value) + 273.15


def k_to_c(value: float) -> float:
    """Convert Kelvin to Celsius."""
    return float(value) - 273.15


def l_to_m3(value: float) -> float:
    """Convert L to m3."""
    return float(value) / 1000.0


def m3_to_l(value: float) -> float:
    """Convert m3 to L."""
    return float(value) * 1000.0


def kj_h_to_kw(value: float) -> float:
    """Convert kJ/h to kW."""
    return float(value) / 3600.0


def kw_to_kj_h(value: float) -> float:
    """Convert kW to kJ/h."""
    return float(value) * 3600.0


def g_mol_to_kg_mol(value: float) -> float:
    """Convert g/mol to kg/mol."""
    return float(value) / 1000.0


def kg_mol_to_g_mol(value: float) -> float:
    """Convert kg/mol to g/mol."""
    return float(value) * 1000.0


def wt_percent_to_fraction(value: float) -> float:
    """Convert wt% to mass fraction."""
    return float(value) / 100.0


def fraction_to_wt_percent(value: float) -> float:
    """Convert mass fraction to wt%."""
    return float(value) * 100.0


def _sum_values(values: Mapping[str, float] | Sequence[float]) -> float:
    """Return numeric sum for mappings or sequences."""
    if isinstance(values, Mapping):
        return sum(float(v) for v in values.values())
    return sum(float(v) for v in values)


def assert_temperature_K(value: float, name: str = "temperature_K") -> None:
    """Assert an absolute temperature is physically valid."""
    if float(value) <= 0.0:
        raise ValueError(f"{name} must be above 0 K")


def assert_pressure_Pa(value: float, name: str = "pressure_Pa") -> None:
    """Assert a pressure is positive."""
    if float(value) <= 0.0:
        raise ValueError(f"{name} must be positive")


def assert_mass_flow_nonnegative(value: float, name: str = "mass_flow") -> None:
    """Assert a mass flow is non-negative."""
    if float(value) < -1.0e-12:
        raise ValueError(f"{name} must be non-negative")


def assert_mole_fraction_sum(values: Mapping[str, float] | Sequence[float], tolerance: float = 1.0e-6) -> None:
    """Assert mole fractions sum to one within tolerance."""
    total = _sum_values(values)
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"mole fractions must sum to 1.0, got {total:.8g}")


def assert_weight_percent_sum(values: Mapping[str, float] | Sequence[float], tolerance: float = 1.0e-3) -> None:
    """Assert weight percentages sum to 100 within tolerance."""
    total = _sum_values(values)
    if abs(total - 100.0) > tolerance:
        raise ValueError(f"weight percentages must sum to 100, got {total:.8g}")


def assert_heat_duty_sign(value: float, exothermic: bool = True, name: str = "Q_rxn") -> None:
    """Assert heat-duty sign convention.

    For exothermic polymerization the returned heat-removal duty is positive.
    """
    if exothermic and float(value) < -1.0e-12:
        raise ValueError(f"{name} must be positive for exothermic heat release")
    if not exothermic and float(value) > 1.0e-12:
        raise ValueError(f"{name} must be negative for endothermic duty convention")


def assert_conversion_range(value: float, as_percent: bool = False, name: str = "conversion") -> None:
    """Assert conversion lies in [0,1] or [0,100]."""
    upper = 100.0 if as_percent else 1.0
    if float(value) < -1.0e-12 or float(value) > upper + 1.0e-12:
        raise ValueError(f"{name} must be between 0 and {upper:g}")


def relative_error(reference: float, actual: float) -> float:
    """Return a stable relative error."""
    return safe_divide(float(actual) - float(reference), max(abs(float(reference)), TINY), 0.0)
