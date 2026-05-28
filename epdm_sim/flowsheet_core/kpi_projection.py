"""KPI projection helpers with physical bounds."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def project_kpis_with_bounds(kpis: dict[str, Any]) -> dict[str, Any]:
    """Project selected KPI values into physical reporting bounds."""
    out = dict(kpis)
    for key in ["conversion_pct", "conversion"]:
        if key in out:
            hi = 100.0 if key.endswith("pct") else 1.0
            out[key] = float(np.clip(float(out[key]), 0.0, hi))
    for key in ["polymer_kg_h", "heat_duty_kW", "cooling_margin_kW"]:
        if key in out and key != "cooling_margin_kW":
            out[key] = max(float(out[key]), 0.0)
    out["projection_applied"] = True
    return out


def kpi_projection_dataframe(kpis: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return projected KPI table."""
    return pd.DataFrame([project_kpis_with_bounds(kpis or {"conversion": 0.5, "polymer_kg_h": 1.0})])
