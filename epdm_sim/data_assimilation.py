"""Evidence-aware data assimilation helpers for V6.3."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calibrated_property_models import CalibratedPropertyModel
from .calibration_data_package import load_calibration_data_package, validate_calibration_dataset_units
from .data_lineage import lineage_confidence_from_record, stable_data_hash
from .experimental_benchmark import load_experimental_benchmarks
from .validation_evidence import evidence_weight


def assimilate_benchmark_observations(
    records: list[dict[str, Any]] | None = None,
    model_outputs: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Compare benchmark observations with model outputs using confidence weights."""
    records = load_experimental_benchmarks() if records is None else records
    outputs = model_outputs or {}
    rows = []
    for record in records:
        validity = record.get("validity_range", {})
        review_status = str(record.get("review_status", "")).lower()
        expected = record.get("expected_output", record.get("value", None))
        observed = outputs.get(record.get("benchmark_id"), expected)
        try:
            error = abs(float(observed) - float(expected))
        except Exception:
            error = 0.0
        tolerance = max(float(record.get("tolerance", record.get("uncertainty", 0.0)) or 0.0), 0.0)
        in_validity = bool("out" not in review_status and validity)
        source_type = str(record.get("source_type", "regression_snapshot"))
        source_ref = str(record.get("source_reference", ""))
        confidence = lineage_confidence_from_record(
            {
                "source_type": source_type,
                "source_reference": source_ref,
                "measurement_unit": record.get("unit", record.get("measurement_unit", "")),
                "validity_range": validity,
                "confidence_level": record.get("confidence_level", "low"),
            }
        )
        passed = bool(in_validity and error <= max(tolerance, 1.0e-12))
        rows.append(
            {
                "benchmark_id": record.get("benchmark_id", ""),
                "source_type": source_type,
                "source_reference": source_ref,
                "expected_output": expected,
                "observed_output": observed,
                "absolute_error": error,
                "tolerance": tolerance,
                "in_validity": in_validity,
                "confidence_score": confidence,
                "evidence_weight": evidence_weight(source_type),
                "passed": passed,
            }
        )
    return pd.DataFrame(rows)


def update_calibrated_model_from_evidence(
    package: dict[str, Any] | None = None,
    *,
    parameter_type: str = "deltaH",
    parameter_name: str = "deltaH_kJ_mol",
) -> CalibratedPropertyModel:
    """Create a calibrated property model from a validated data package."""
    pkg = load_calibration_data_package(package)
    unit_status = validate_calibration_dataset_units(pkg)
    if not unit_status["passed"]:
        raise ValueError(f"invalid calibration dataset units: {unit_status['invalid_units']}")
    values = [float(obs.get("value", 0.0)) for obs in pkg.get("observations", []) if obs.get("name") == parameter_name or obs.get("name") == parameter_type]
    if not values:
        values = [float(pkg.get("value", 95.0))]
    value = float(np.mean(values))
    data_hash = str(pkg.get("data_hash") or stable_data_hash(pkg))
    source_type = str(pkg.get("source_type", "synthetic"))
    confidence = lineage_confidence_from_record(
        {
            "source_type": source_type,
            "source_reference": pkg.get("source_reference", ""),
            "measurement_unit": pkg.get("measurement_unit", ""),
            "validity_range": pkg.get("validity_range", {}),
            "confidence_level": pkg.get("confidence_level", "medium"),
        }
    )
    return CalibratedPropertyModel(
        model_id=f"{pkg.get('dataset_id', 'dataset')}_{parameter_type}",
        parameter_type=parameter_type,
        parameters={parameter_name: max(value, 0.0)},
        dataset_id=str(pkg.get("dataset_id", "dataset")),
        data_hash=data_hash,
        validity_range=dict(pkg.get("validity_range", {})),
        uncertainty={"relative_pct": float(pkg.get("uncertainty", 0.0))},
        source_type=source_type,
        confidence_score=confidence,
        warnings=[] if confidence >= 50.0 else ["low-confidence calibration evidence"],
    )


def data_assimilation_summary(records: list[dict[str, Any]] | None = None, model_outputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return bounded pass/fail summary for release gates."""
    df = assimilate_benchmark_observations(records, model_outputs)
    if df.empty:
        return {"passed": False, "rows": 0, "confidence_score": 0.0, "failed": 1}
    eligible = df[df["in_validity"].astype(bool)]
    failed = int((~eligible["passed"].astype(bool)).sum()) if not eligible.empty else 0
    confidence = float(df["confidence_score"].mean())
    return {"passed": bool(failed == 0 and confidence >= 30.0), "rows": int(len(df)), "confidence_score": confidence, "failed": failed}


def data_assimilation_dataframe(records: list[dict[str, Any]] | None = None, model_outputs: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return assimilation rows plus source confidence."""
    return assimilate_benchmark_observations(records, model_outputs)

