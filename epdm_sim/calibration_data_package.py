"""Calibration data package validation for V6.3."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd

from .data_lineage import build_data_lineage_record, stable_data_hash

SUPPORTED_UNITS = {"kg/h", "mol/L", "mol/m3", "kW", "kJ/h", "Pa.s", "cP", "MPa", "Pa", "K", "°C", "wt%", "dimensionless"}


def load_calibration_data_package(package: str | Path | dict[str, Any] | None = None) -> dict[str, Any]:
    """Load or build a calibration data package without mutating defaults."""
    if package is None:
        return {
            "dataset_id": "synthetic_v6_3_calibration",
            "source_type": "synthetic",
            "source_reference": "internal synthetic standard case",
            "measurement_unit": "dimensionless",
            "uncertainty": 0.05,
            "validity_range": {"temperature_C": [80.0, 130.0], "pressure_MPa": [0.5, 2.0]},
            "observations": [{"name": "polymer_yield", "value": 1.0, "unit": "dimensionless"}],
        }
    if isinstance(package, (str, Path)):
        return json.loads(Path(package).read_text(encoding="utf-8"))
    return dict(package)


def validate_calibration_dataset_units(package: dict[str, Any]) -> dict[str, Any]:
    """Validate package-level and observation units."""
    units = [str(package.get("measurement_unit", ""))]
    units.extend(str(row.get("unit", "")) for row in package.get("observations", []))
    invalid = [unit for unit in units if unit and unit not in SUPPORTED_UNITS]
    return {
        "dataset_id": package.get("dataset_id", ""),
        "passed": not invalid,
        "invalid_units": "; ".join(invalid),
        "checked_units": "; ".join(units),
    }


def calibration_data_lineage_dataframe(package: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return lineage rows for a calibration package."""
    pkg = load_calibration_data_package(package)
    payload = dict(pkg)
    payload["benchmark_id"] = payload.get("dataset_id", "calibration_dataset")
    payload["data_hash"] = payload.get("data_hash") or stable_data_hash(payload)
    record = build_data_lineage_record(payload)
    row = record.as_dict()
    row["unit_check_passed"] = validate_calibration_dataset_units(pkg)["passed"]
    row["observation_count"] = len(pkg.get("observations", []))
    return pd.DataFrame([row])


def calibration_package_dataframe(package: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return package observations as a report table."""
    pkg = load_calibration_data_package(package)
    rows = []
    for obs in pkg.get("observations", []):
        rows.append({**obs, "dataset_id": pkg.get("dataset_id", ""), "source_type": pkg.get("source_type", "")})
    return pd.DataFrame(rows or [{"dataset_id": pkg.get("dataset_id", ""), "status": "no_observations"}])

