"""Reactor heat-release helper equations."""

from __future__ import annotations

import pandas as pd


def heat_release_from_conversion(monomer_mol_h: float, conversion: float, delta_h_kj_mol: float) -> dict[str, float | bool]:
    """Return exothermic heat release in kW from consumed monomer."""
    consumed = max(float(monomer_mol_h), 0.0) * min(max(float(conversion), 0.0), 1.0)
    q_kw = consumed * abs(float(delta_h_kj_mol)) / 3600.0
    return {"consumed_mol_h": consumed, "delta_h_kj_mol": abs(float(delta_h_kj_mol)), "Q_rxn_kW": q_kw, "passed": q_kw >= 0.0}


def heat_release_dataframe(monomer_mol_h: float = 1000.0, conversion: float = 0.5, delta_h_kj_mol: float = 95.0) -> pd.DataFrame:
    """Return heat-release record as a DataFrame."""
    return pd.DataFrame([heat_release_from_conversion(monomer_mol_h, conversion, delta_h_kj_mol)])
