"""Experimental time-series data import and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TIME_SERIES_COLUMNS = [
    "run_id",
    "time_min",
    "temperature_C",
    "pressure_MPa",
    "feed_ethylene",
    "feed_propylene",
    "feed_ENB",
    "feed_H2",
    "Q_rxn_kW",
    "Q_removed_kW",
    "solids_wt",
    "viscosity_Pa_s",
    "Mw",
    "Mooney",
    "notes",
]


@dataclass(frozen=True)
class TimeSeriesValidationResult:
    """Validation result for experimental dynamic profiles."""

    passed: bool
    warnings: list[str]
    required_columns: list[str]
    present_columns: list[str]

    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({"passed": [self.passed], "warnings": ["; ".join(self.warnings)], "required_columns": [", ".join(self.required_columns)], "present_columns": [", ".join(self.present_columns)]})


def load_time_series_csv_or_excel(path: str | Path) -> pd.DataFrame:
    """Load an experimental profile from CSV or Excel."""
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p)
    return pd.read_csv(p)


def validate_time_series_schema(df: pd.DataFrame) -> TimeSeriesValidationResult:
    """Validate dynamic profile columns, monotonic time and finite key values."""
    warnings: list[str] = []
    required = ["run_id", "time_min"]
    missing_required = [col for col in required if col not in df.columns]
    if missing_required:
        warnings.append(f"missing required columns: {missing_required}")
    missing_optional = [col for col in TIME_SERIES_COLUMNS if col not in df.columns]
    if missing_optional:
        warnings.append(f"missing optional columns: {missing_optional}")
    if "time_min" in df.columns:
        time = pd.to_numeric(df["time_min"], errors="coerce")
        if time.isna().any():
            warnings.append("time_min contains non-finite values")
        if (time.diff().dropna() < -1.0e-12).any():
            warnings.append("time_min must be monotonically nondecreasing")
    for col in ["temperature_C", "pressure_MPa", "Q_rxn_kW", "Q_removed_kW", "solids_wt", "viscosity_Pa_s", "Mw", "Mooney"]:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            if values.notna().any() and not np.isfinite(values.dropna()).all():
                warnings.append(f"{col} contains non-finite values")
            if col in {"pressure_MPa", "viscosity_Pa_s", "Mw", "Mooney"} and (values.dropna() < 0.0).any():
                warnings.append(f"{col} contains negative physical values")
    return TimeSeriesValidationResult(not any("required" in w or "monotonically" in w or "non-finite" in w for w in warnings), warnings, required, list(df.columns))


def normalize_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with known numeric columns converted to numeric dtype."""
    out = df.copy()
    for col in TIME_SERIES_COLUMNS:
        if col in out.columns and col not in {"run_id", "notes"}:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out
