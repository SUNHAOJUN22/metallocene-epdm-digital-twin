"""Henry-law style gas solubility correlations for EPDM solution polymerization."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .utils import R_GAS, TINY, clamp, data_path, load_json, positive


@dataclass(frozen=True)
class SolubilityRecord:
    """Reference solubility model parameters."""

    component: str
    solvent: str
    solubility_ref_mol_L_MPa: float
    dH_solution_J_mol: float
    T_ref_K: float = 373.15


_BASE_SOLUBILITY = {
    ("ethylene", "hexane"): SolubilityRecord("ethylene", "hexane", 0.18, -5500.0),
    ("ethylene", "heptane"): SolubilityRecord("ethylene", "heptane", 0.17, -5400.0),
    ("ethylene", "toluene"): SolubilityRecord("ethylene", "toluene", 0.15, -5200.0),
    ("propylene", "hexane"): SolubilityRecord("propylene", "hexane", 0.24, -6500.0),
    ("propylene", "heptane"): SolubilityRecord("propylene", "heptane", 0.23, -6400.0),
    ("propylene", "toluene"): SolubilityRecord("propylene", "toluene", 0.20, -6100.0),
    ("hydrogen", "hexane"): SolubilityRecord("hydrogen", "hexane", 0.015, -1200.0),
    ("hydrogen", "heptane"): SolubilityRecord("hydrogen", "heptane", 0.014, -1100.0),
    ("hydrogen", "toluene"): SolubilityRecord("hydrogen", "toluene", 0.011, -900.0),
}

_PARAMETER_CACHE: dict[str, Any] | None = None


def _load_solubility_payload() -> dict[str, Any]:
    """Load Henry parameter data from JSON with a hardcoded fallback."""
    global _PARAMETER_CACHE
    if _PARAMETER_CACHE is not None:
        return _PARAMETER_CACHE
    path = data_path("solubility_parameters.json")
    try:
        payload = load_json(path)
    except Exception:
        payload = {
            "records": [record.__dict__ for record in _BASE_SOLUBILITY.values()],
            "catalyst_family_factors": {},
            "solvent_factors": {},
        }
    payload.setdefault("records", [record.__dict__ for record in _BASE_SOLUBILITY.values()])
    payload.setdefault("catalyst_family_factors", {})
    payload.setdefault("solvent_factors", {})
    _PARAMETER_CACHE = payload
    return payload


def load_solubility_records() -> dict[tuple[str, str], SolubilityRecord]:
    """Return gas solubility records loaded from data/solubility_parameters.json."""
    payload = _load_solubility_payload()
    records: dict[tuple[str, str], SolubilityRecord] = {}
    for item in payload.get("records", []):
        try:
            record = SolubilityRecord(
                component=str(item["component"]),
                solvent=str(item["solvent"]),
                solubility_ref_mol_L_MPa=float(item["solubility_ref_mol_L_MPa"]),
                dH_solution_J_mol=float(item["dH_solution_J_mol"]),
                T_ref_K=float(item.get("T_ref_K", 373.15)),
            )
            records[(record.component, record.solvent)] = record
        except Exception:
            continue
    return records or dict(_BASE_SOLUBILITY)


def solubility_records_dataframe() -> pd.DataFrame:
    """Return the built-in gas solubility records."""
    payload = _load_solubility_payload()
    rows = []
    for record in load_solubility_records().values():
        item = record.__dict__.copy()
        item["source"] = "data/solubility_parameters.json"
        rows.append(item)
    if not rows:
        rows = [record.__dict__ for record in _BASE_SOLUBILITY.values()]
    df = pd.DataFrame(rows)
    df.attrs["metadata"] = payload.get("metadata", {})
    return df


def calibrate_henry_parameters(
    observations: pd.DataFrame,
    *,
    component: str,
    solvent: str,
    initial_ref: float | None = None,
) -> SolubilityRecord:
    """Fit a single Henry reference coefficient from measured Cstar data.

    Required columns are temperature_K, partial_pressure_MPa and C_star_mol_L.
    The enthalpy term is kept at the default value because most early R&D data
    sets do not contain enough temperature leverage for stable joint fitting.
    """
    records = load_solubility_records()
    base = records.get((component, solvent)) or records.get((component, "hexane"))
    if base is None:
        base = SolubilityRecord(component, solvent, initial_ref or 0.1, -2500.0)
    df = observations.copy()
    if df.empty:
        return base
    ratios = []
    for _, row in df.iterrows():
        pressure = positive(row.get("partial_pressure_MPa", 0.0))
        measured = positive(row.get("C_star_mol_L", 0.0))
        T = max(float(row.get("temperature_K", base.T_ref_K)), 1.0)
        if pressure <= 0 or measured <= 0:
            continue
        exponent = -base.dH_solution_J_mol / R_GAS * (1.0 / T - 1.0 / base.T_ref_K)
        ratios.append(measured / max(pressure * math.exp(clamp(exponent, -2.0, 2.0)), TINY))
    fitted_ref = float(pd.Series(ratios).median()) if ratios else base.solubility_ref_mol_L_MPa
    return SolubilityRecord(component, solvent, clamp(fitted_ref, 1.0e-5, 20.0), base.dH_solution_J_mol, base.T_ref_K)


def liquid_saturation_concentration_mol_L(
    component: str,
    solvent: str,
    temperature_K: float,
    partial_pressure_MPa: float,
    *,
    catalyst_family: str | None = None,
    modifier: float = 1.0,
) -> float:
    """Return saturated liquid concentration in mol/L with high-pressure Poynting correction."""
    clean_solvent = solvent if solvent in {"hexane", "heptane", "toluene"} else "hexane"
    payload = _load_solubility_payload()
    records = load_solubility_records()
    record = records.get((component, clean_solvent))
    T = max(float(temperature_K), 1.0)
    pressure = positive(partial_pressure_MPa)
    
    # 1. Base Henry model with temperature dependence
    exponent = -record.dH_solution_J_mol / R_GAS * (1.0 / T - 1.0 / record.T_ref_K)
    c_base = record.solubility_ref_mol_L_MPa * pressure * math.exp(clamp(exponent, -5.0, 5.0))
    
    # 2. Poynting Correction for High Pressure (> 2 MPa)
    # Approximate partial molar volumes in m3/mol (e.g. 50 cm3/mol = 5e-5 m3/mol)
    v_partial = {"ethylene": 5.0e-5, "propylene": 6.5e-5, "hydrogen": 3.0e-5}.get(component, 4.5e-5)
    
    # Poynting factor: exp( V * (P - Pref) / RT )
    # P is in MPa, so we convert to Pa using 1e6
    p_ref_MPa = 0.101325
    poynting = math.exp(clamp(v_partial * (pressure - p_ref_MPa) * 1.0e6 / (R_GAS * T), -0.5, 0.5))
    
    # 3. Apply factors
    family_factor = 1.0
    if catalyst_family:
        family_factors = payload.get("catalyst_family_factors", {})
        family_factor = float(family_factors.get(catalyst_family, family_factors.get(catalyst_family.strip(), 1.0)))
        if family_factor == 1.0:
            family = catalyst_family.lower()
            if "cgc" in family:
                family_factor = 1.05
            elif "mono" in family:
                family_factor = 0.98
                
    solvent_factor = float(payload.get("solvent_factors", {}).get(clean_solvent, 1.0))
    
    return clamp(c_base * poynting * family_factor * solvent_factor * modifier, 0.0, 15.0)


def gas_liquid_saturation_table(
    temperature_K: float,
    pressure_MPa: float,
    gas_mole_fractions: dict[str, float],
    solvent: str = "hexane",
) -> pd.DataFrame:
    """Return saturation concentrations for C2/C3/H2 gas mixture."""
    rows = []
    for component in ["ethylene", "propylene", "hydrogen"]:
        y = positive(gas_mole_fractions.get(component, 0.0))
        rows.append(
            {
                "component": component,
                "solvent": solvent,
                "y_gas": y,
                "partial_pressure_MPa": y * pressure_MPa,
                "C_star_mol_L": liquid_saturation_concentration_mol_L(component, solvent, temperature_K, y * pressure_MPa),
            }
        )
    return pd.DataFrame(rows)


def gas_mole_fractions_from_feeds(ethylene: float, propylene: float, hydrogen: float) -> dict[str, float]:
    """Build gas mole fractions from arbitrary positive mole-like feed values."""
    total = max(positive(ethylene) + positive(propylene) + positive(hydrogen), TINY)
    return {
        "ethylene": positive(ethylene) / total,
        "propylene": positive(propylene) / total,
        "hydrogen": positive(hydrogen) / total,
    }


def henry_cstar_comparison(
    temperature_K: float,
    pressure_MPa: float,
    gas_mole_fractions: dict[str, float],
    solvent: str = "hexane",
    catalyst_family: str | None = None,
) -> pd.DataFrame:
    """Return a table comparing base and catalyst-corrected Henry Cstar values."""
    rows = []
    for component in ["ethylene", "propylene", "hydrogen"]:
        partial = positive(gas_mole_fractions.get(component, 0.0)) * pressure_MPa
        base = liquid_saturation_concentration_mol_L(component, solvent, temperature_K, partial)
        corrected = liquid_saturation_concentration_mol_L(
            component,
            solvent,
            temperature_K,
            partial,
            catalyst_family=catalyst_family,
        )
        rows.append(
            {
                "component": component,
                "solvent": solvent,
                "partial_pressure_MPa": partial,
                "Cstar_base_mol_L": base,
                "Cstar_corrected_mol_L": corrected,
                "catalyst_family": catalyst_family or "none",
            }
        )
    return pd.DataFrame(rows)
