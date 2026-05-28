"""Unit-operation residual helpers."""

from __future__ import annotations

import pandas as pd

from .energy_closure import energy_closure_record
from .material_closure import material_closure_record


def unit_residuals_dataframe() -> pd.DataFrame:
    """Return default unit residual examples for release-gate schema."""
    rows = [
        {"unit_operation": "reactor", **material_closure_record(1.0, 1.0, 0.0)},
        {"unit_operation": "heat_balance", **energy_closure_record(1.0, 1.0, 0.0)},
    ]
    return pd.DataFrame(rows)
