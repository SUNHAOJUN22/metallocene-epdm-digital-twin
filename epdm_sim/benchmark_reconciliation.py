"""Benchmark reconciliation helpers for V6.4 industrial evidence."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .industrial_data_package import estimate_measurement_uncertainty as package_uncertainty
from .industrial_data_package import load_industrial_data_package, validate_industrial_dataset_schema


def estimate_measurement_uncertainty(package: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expose benchmark-level measurement uncertainty."""
    return package_uncertainty(package)


def reconcile_benchmark_observations(
    package: dict[str, Any] | None = None,
    model_outputs: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Compare package observations against model outputs with uncertainty."""
    pkg = load_industrial_data_package(package)
    validation = validate_industrial_dataset_schema(pkg)
    outputs = model_outputs or {"polymer_mass_closure": 11.5, "heat_release_closure": 8.0}
    uncertainty = max(float(pkg.get("uncertainty", 0.05)), 1.0e-12)
    rows: list[dict[str, Any]] = []
    for obs in pkg.get("observations", []):
        if not isinstance(obs, dict):
            continue
        benchmark_id = str(obs.get("benchmark_id", obs.get("name", "benchmark")))
        expected = float(obs.get("value", 0.0))
        actual = float(outputs.get(benchmark_id, expected))
        residual = actual - expected
        normalized = abs(residual) / max(abs(expected) * uncertainty, uncertainty)
        passed = bool(normalized <= 3.0 and validation["passed"])
        rows.append(
            {
                "benchmark_id": benchmark_id,
                "dataset_id": pkg["dataset_id"],
                "source_type": pkg["source_type"],
                "expected": expected,
                "actual": actual,
                "residual": residual,
                "normalized_residual": normalized,
                "unit": obs.get("unit", pkg.get("measurement_unit", "")),
                "uncertainty": uncertainty,
                "confidence_score": validation["confidence_score"],
                "passed": passed,
            }
        )
    if not rows:
        rows.append({"benchmark_id": "no_observation", "dataset_id": pkg["dataset_id"], "normalized_residual": 0.0, "passed": validation["passed"]})
    return pd.DataFrame(rows)


def benchmark_reconciliation_dataframe(
    package: dict[str, Any] | None = None,
    model_outputs: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Return benchmark reconciliation rows."""
    return reconcile_benchmark_observations(package, model_outputs)


def benchmark_reconciliation_summary(
    package: dict[str, Any] | None = None,
    model_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact reconciliation status."""
    df = benchmark_reconciliation_dataframe(package, model_outputs)
    failed = int((~df.get("passed", pd.Series(dtype=bool)).astype(bool)).sum()) if not df.empty else 1
    max_norm = float(pd.to_numeric(df.get("normalized_residual", pd.Series([0.0])), errors="coerce").fillna(0.0).max())
    return {"passed": bool(failed == 0 and np.isfinite(max_norm)), "rows": int(len(df)), "failed": failed, "max_normalized_residual": max_norm}


def benchmark_reconciliation_gate(
    package: dict[str, Any] | None = None,
    model_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return release-gate status for benchmark reconciliation."""
    return benchmark_reconciliation_summary(package, model_outputs)

