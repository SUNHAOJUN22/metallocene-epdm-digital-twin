"""Reactor output table helpers."""

from __future__ import annotations

import pandas as pd


def reactor_output_dataframe(kpis: dict[str, float]) -> pd.DataFrame:
    """Return reactor KPI dictionary as a table."""
    return pd.DataFrame([{"kpi": key, "value": value} for key, value in kpis.items()])

