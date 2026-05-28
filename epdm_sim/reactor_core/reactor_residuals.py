"""Reactor residual report helpers."""

from __future__ import annotations

import pandas as pd

from .reaction_balance import reaction_mass_balance_record


def reactor_residuals_dataframe(feed_kg_h: float = 1.0, polymer_kg_h: float = 1.0, unreacted_kg_h: float = 0.0) -> pd.DataFrame:
    """Return reactor residual rows."""
    row = reaction_mass_balance_record(feed_kg_h, polymer_kg_h, unreacted_kg_h)
    row["residual_id"] = "reactor_material_balance"
    return pd.DataFrame([row])
