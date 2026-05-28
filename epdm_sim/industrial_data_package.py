"""Industrial calibration data package helpers for V6.4."""

from __future__ import annotations

from typing import Any
import hashlib
import json

import pandas as pd

VALID_SOURCE_TYPES = {"plant", "experiment", "literature", "synthetic", "regression_snapshot"}
VALID_UNITS = {"wt%", "kg/h", "g/h", "mol/L", "mol/m3", "K", "degC", "C", "MPa", "Pa", "kW", "kJ/h", "Pa.s", "cP", "dimensionless"}
SOURCE_WEIGHTS = {"plant": 1.0, "experiment": 0.85, "literature": 0.70, "synthetic": 0.40, "regression_snapshot": 0.20}


def _stable_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_industrial_data_package(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load or normalize an industrial calibration data package."""
    package = dict(
        payload
        or {
            "dataset_id": "plant_v6_4_reference",
            "source_type": "plant",
            "source_reference": "plant historian reconciled batch set",
            "measurement_unit": "kg/h",
            "uncertainty": 0.05,
            "validity_range": {"temperature_C": [80.0, 130.0], "pressure_MPa": [0.7, 2.0]},
            "observations": [{"benchmark_id": "polymer_mass_closure", "value": 11.5, "unit": "kg/h"}],
        }
    )
    package.setdefault("dataset_id", "industrial_dataset")
    package.setdefault("source_type", "synthetic")
    package.setdefault("source_reference", "")
    package.setdefault("measurement_unit", "dimensionless")
    package.setdefault("uncertainty", 0.20)
    package.setdefault("validity_range", {})
    package.setdefault("observations", [])
    package["data_hash"] = str(package.get("data_hash") or _stable_hash({k: v for k, v in package.items() if k != "data_hash"}))
    return package


def validate_industrial_dataset_schema(package: dict[str, Any]) -> dict[str, Any]:
    """Validate source, unit, uncertainty and validity metadata."""
    pkg = load_industrial_data_package(package)
    missing = [key for key in ["dataset_id", "source_type", "measurement_unit", "uncertainty", "validity_range", "data_hash"] if not pkg.get(key)]
    invalid_units = []
    units = [str(pkg.get("measurement_unit", ""))]
    units.extend(str(obs.get("unit", "")) for obs in pkg.get("observations", []) if isinstance(obs, dict))
    for unit in units:
        if unit and unit not in VALID_UNITS:
            invalid_units.append(unit)
    source_type = str(pkg.get("source_type", ""))
    missing_source = source_type in {"plant", "experiment", "literature"} and not str(pkg.get("source_reference", "")).strip()
    uncertainty = float(pkg.get("uncertainty", 1.0))
    passed = bool(not missing and not invalid_units and source_type in VALID_SOURCE_TYPES and uncertainty >= 0.0 and not missing_source)
    confidence = 100.0 * SOURCE_WEIGHTS.get(source_type, 0.25)
    if missing_source:
        confidence *= 0.5
    if invalid_units:
        confidence *= 0.5
    return {
        "dataset_id": pkg["dataset_id"],
        "passed": passed,
        "source_type": source_type,
        "missing": "; ".join(missing),
        "invalid_units": "; ".join(sorted(set(invalid_units))),
        "missing_source_reference": missing_source,
        "confidence_score": confidence,
        "data_hash": pkg["data_hash"],
    }


def estimate_measurement_uncertainty(package: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return bounded uncertainty estimate for an industrial data package."""
    pkg = load_industrial_data_package(package)
    source_type = str(pkg.get("source_type", "synthetic"))
    base = float(pkg.get("uncertainty", 0.20))
    weight = SOURCE_WEIGHTS.get(source_type, 0.25)
    effective = max(base / max(weight, 1.0e-12), 0.0)
    return {"dataset_id": pkg["dataset_id"], "source_type": source_type, "uncertainty": base, "effective_uncertainty": effective, "passed": effective >= 0.0}


def industrial_data_lineage_dataframe(package: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return data-lineage rows for an industrial package."""
    pkg = load_industrial_data_package(package)
    validation = validate_industrial_dataset_schema(pkg)
    return pd.DataFrame(
        [
            {
                "dataset_id": pkg["dataset_id"],
                "source_type": pkg["source_type"],
                "source_reference": pkg.get("source_reference", ""),
                "measurement_unit": pkg.get("measurement_unit", ""),
                "uncertainty": float(pkg.get("uncertainty", 0.0)),
                "validity_range": json.dumps(pkg.get("validity_range", {}), sort_keys=True),
                "data_hash": pkg["data_hash"],
                "confidence_score": validation["confidence_score"],
                "passed": validation["passed"],
            }
        ]
    )


def industrial_data_package_dataframe(package: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return package observations with validation metadata."""
    pkg = load_industrial_data_package(package)
    validation = validate_industrial_dataset_schema(pkg)
    observations = pkg.get("observations", []) or [{"benchmark_id": "no_observation", "value": 0.0, "unit": pkg.get("measurement_unit", "dimensionless")}]
    rows = []
    for obs in observations:
        row = dict(obs)
        row.update(
            {
                "dataset_id": pkg["dataset_id"],
                "source_type": pkg["source_type"],
                "source_reference": pkg.get("source_reference", ""),
                "data_hash": pkg["data_hash"],
                "confidence_score": validation["confidence_score"],
                "passed": validation["passed"],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)

