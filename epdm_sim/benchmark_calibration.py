"""Benchmark calibration and data-gap scoring for V5.5."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .experimental_benchmark import benchmark_data_hash, experimental_benchmarks_dataframe, load_experimental_benchmarks


SOURCE_WEIGHTS = {
    "plant": 1.00,
    "experiment": 0.85,
    "literature": 0.70,
    "synthetic": 0.45,
    "regression_snapshot": 0.25,
}


def benchmark_weight_by_confidence(source_type: str, confidence_level: str | float = "medium") -> float:
    """Return a 0-1 benchmark weight from source type and confidence."""
    source_weight = SOURCE_WEIGHTS.get(str(source_type).lower(), 0.25)
    if isinstance(confidence_level, (int, float)):
        confidence_weight = max(0.0, min(float(confidence_level) / 100.0, 1.0))
    else:
        confidence_weight = {"low": 0.35, "medium": 0.65, "high": 0.90, "plant": 0.98}.get(str(confidence_level).lower(), 0.35)
    return float(source_weight * confidence_weight)


def _within_validity(record: dict[str, Any]) -> bool:
    review_status = str(record.get("review_status", "accepted")).lower()
    if "out" in review_status:
        return False
    validity = record.get("validity_range", {}) or {}
    if isinstance(validity, str):
        return "outside" not in validity.lower()
    if not isinstance(validity, dict):
        return True
    for value in validity.values():
        if isinstance(value, str) and "outside" in value.lower():
            return False
    return True


def compare_model_to_experimental_benchmark(model_outputs: dict[str, Any] | None = None) -> pd.DataFrame:
    """Compare supplied model outputs to benchmark expected values.

    Missing model outputs are reported as ``not_run``.  The function is
    intentionally read-only and does not run any model.
    """
    model_outputs = model_outputs or {}
    rows: list[dict[str, Any]] = []
    for record in load_experimental_benchmarks():
        benchmark_id = str(record.get("benchmark_id", ""))
        expected = record.get("expected_output", {})
        if not isinstance(expected, dict):
            expected = {"value": expected}
        tolerance = float(record.get("tolerance", 0.0))
        weight = benchmark_weight_by_confidence(record.get("source_type", "regression_snapshot"), record.get("confidence_level", "low"))
        in_scope = _within_validity(record)
        for metric, expected_value in expected.items():
            actual = model_outputs.get(metric)
            if actual is None:
                passed = False
                residual = None
                status = "not_run"
            else:
                try:
                    residual = float(actual) - float(expected_value)
                    passed = abs(residual) <= tolerance
                    status = "passed" if passed else "failed"
                except (TypeError, ValueError):
                    residual = None
                    passed = False
                    status = "non_numeric_expected"
            rows.append(
                {
                    "benchmark_id": benchmark_id,
                    "metric": metric,
                    "expected": expected_value,
                    "actual": actual,
                    "residual": residual,
                    "unit": record.get("unit", ""),
                    "tolerance": tolerance,
                    "source_type": record.get("source_type", "regression_snapshot"),
                    "confidence_level": record.get("confidence_level", "low"),
                    "weight": weight,
                    "within_validity": in_scope,
                    "passed": bool(passed and in_scope),
                    "status": "out_of_validity" if not in_scope else status,
                    "data_hash": record.get("data_hash") or benchmark_data_hash(record),
                }
            )
    return pd.DataFrame(rows)


def benchmark_residual_dataframe(model_outputs: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return weighted benchmark residual rows."""
    df = compare_model_to_experimental_benchmark(model_outputs)
    if df.empty:
        return pd.DataFrame(columns=["benchmark_id", "weighted_abs_residual", "passed"])
    residual = pd.to_numeric(df["residual"], errors="coerce")
    tolerance = pd.to_numeric(df["tolerance"], errors="coerce").fillna(0.0)
    weight = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
    df["weighted_abs_residual"] = residual.fillna(tolerance.abs() + 1.0).abs() * weight
    return df


def update_model_confidence_from_benchmarks(base_score: float, model_outputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a benchmark-adjusted confidence score."""
    df = benchmark_residual_dataframe(model_outputs)
    if df.empty:
        return {"base_score": float(base_score), "adjusted_score": float(base_score), "benchmark_pass_rate": 0.0}
    valid = df[df["within_validity"].astype(bool)]
    pass_rate = float(valid["passed"].mean()) if not valid.empty else 0.0
    weighted_penalty = min(float(df["weighted_abs_residual"].sum()), 30.0)
    adjusted = max(0.0, min(100.0, float(base_score) + 8.0 * pass_rate - weighted_penalty))
    return {
        "base_score": float(base_score),
        "adjusted_score": adjusted,
        "benchmark_pass_rate": pass_rate,
        "weighted_penalty": weighted_penalty,
        "benchmark_count": int(len(df)),
    }


def recommend_calibration_data_gaps(model_outputs: dict[str, Any] | None = None) -> pd.DataFrame:
    """Recommend next data types from benchmark coverage and failures."""
    df = benchmark_residual_dataframe(model_outputs)
    existing_sources = set(experimental_benchmarks_dataframe().get("source_type", pd.Series(dtype=str)).astype(str).str.lower())
    desired = [
        ("VLE/flash recovery", "phase_equilibrium", "Add pressure/temperature flash recovery data for C2/C3/H2/ENB/solvent."),
        ("reaction calorimetry", "heat_balance", "Add heat-release and cooling duty measurements for deltaH validation."),
        ("solution rheology", "transport", "Add viscosity vs solids/Mw/shear-rate/temperature data."),
        ("GPC/Mooney", "polymer_properties", "Add Mw/PDI/Mooney endpoint validation for calibrated parameter sets."),
        ("dynamic T/P profile", "dynamic_ode", "Add semi-batch time-series T/P/Q profiles for RHS residual validation."),
    ]
    rows = []
    failed_links = set(df.loc[~df.get("passed", pd.Series(dtype=bool)).astype(bool), "benchmark_id"].astype(str)) if not df.empty else set()
    for label, category, reason in desired:
        priority = "medium"
        if "experiment" not in existing_sources and "plant" not in existing_sources:
            priority = "high"
        if any(category in item.lower() for item in failed_links):
            priority = "high"
        rows.append({"data_gap": label, "category": category, "priority": priority, "recommended_action": reason})
    return pd.DataFrame(rows)


def benchmark_calibration_summary(model_outputs: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return benchmark calibration score summary."""
    confidence = update_model_confidence_from_benchmarks(70.0, model_outputs)
    confidence["gate"] = "benchmark_calibration"
    return pd.DataFrame([confidence])
