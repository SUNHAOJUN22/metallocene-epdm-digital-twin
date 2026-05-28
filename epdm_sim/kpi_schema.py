"""Template-aware KPI schema and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class KPI:
    """One normalized KPI row."""

    name: str
    value: float | str
    unit: str
    category: str
    template_id: str
    component_or_segment: str = ""
    compatibility_alias: str = ""
    bounds: tuple[float | None, float | None] = (None, None)
    warning: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "category": self.category,
            "template_id": self.template_id,
            "component_or_segment": self.component_or_segment,
            "compatibility_alias": self.compatibility_alias,
            "lower_bound": self.bounds[0],
            "upper_bound": self.bounds[1],
            "warning": self.warning,
        }


def validate_kpi_bounds(kpis: list[KPI]) -> list[KPI]:
    """Return KPI rows with warnings populated for non-finite/out-of-range values."""
    checked: list[KPI] = []
    for kpi in kpis:
        warning = kpi.warning
        value = kpi.value
        if isinstance(value, (int, float)):
            if not np.isfinite(value):
                warning = "non-finite KPI"
            low, high = kpi.bounds
            if low is not None and value < low - 1.0e-9:
                warning = f"value below lower bound {low}"
            if high is not None and value > high + 1.0e-9:
                warning = f"value above upper bound {high}"
        checked.append(replace(kpi, warning=warning))
    return checked


def kpis_to_dataframe(kpis: list[KPI]) -> pd.DataFrame:
    """Convert KPI rows to a DataFrame."""
    return pd.DataFrame([kpi.as_dict() for kpi in validate_kpi_bounds(kpis)])
