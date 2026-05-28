"""Reactor material-balance helpers."""

from __future__ import annotations

import pandas as pd


def reaction_mass_balance_record(feed_kg_h: float, polymer_kg_h: float, unreacted_kg_h: float = 0.0) -> dict[str, float | bool]:
    """Return a simple reactor mass balance record."""
    lhs = float(feed_kg_h)
    rhs = float(polymer_kg_h) + float(unreacted_kg_h)
    err = lhs - rhs
    return {"feed_kg_h": lhs, "polymer_kg_h": float(polymer_kg_h), "unreacted_kg_h": float(unreacted_kg_h), "error_kg_h": err, "passed": abs(err) <= max(1.0e-6, 0.05 * max(lhs, 1.0))}


def reaction_balance_dataframe(feed_kg_h: float = 1.0, polymer_kg_h: float = 1.0, unreacted_kg_h: float = 0.0) -> pd.DataFrame:
    """Return reactor balance as a DataFrame."""
    return pd.DataFrame([reaction_mass_balance_record(feed_kg_h, polymer_kg_h, unreacted_kg_h)])
