"""Flowsheet energy-closure helpers."""

from __future__ import annotations

import pandas as pd


def energy_closure_record(q_rxn_kW: float, q_removed_kW: float, accumulation_kW: float = 0.0) -> dict[str, float | bool]:
    """Return energy closure for exothermic reaction and cooling duty."""
    lhs = float(q_rxn_kW)
    rhs = float(q_removed_kW) + float(accumulation_kW)
    error = lhs - rhs
    return {"Q_rxn_kW": lhs, "Q_removed_kW": float(q_removed_kW), "accumulation_kW": float(accumulation_kW), "error_kW": error, "passed": abs(error) <= max(1.0e-6, 0.10 * max(abs(lhs), 1.0))}


def energy_closure_dataframe(q_rxn_kW: float = 1.0, q_removed_kW: float = 1.0, accumulation_kW: float = 0.0) -> pd.DataFrame:
    """Return energy closure as a DataFrame."""
    return pd.DataFrame([energy_closure_record(q_rxn_kW, q_removed_kW, accumulation_kW)])
