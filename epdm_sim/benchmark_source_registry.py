"""Benchmark source registry and lineage checks for V5.7."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd

from .benchmark_calibration import benchmark_weight_by_confidence
from .experimental_benchmark import benchmark_data_hash, load_experimental_benchmarks
from .utils import data_path


def load_benchmark_sources(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load benchmark source records, falling back to experimental benchmarks."""
    source_path = Path(path or data_path("benchmark_sources.json"))
    if source_path.exists():
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            records = payload.get("sources", payload) if isinstance(payload, dict) else payload
            if isinstance(records, list):
                return [dict(row) for row in records]
        except Exception:
            pass
    rows = []
    for record in load_experimental_benchmarks():
        rows.append(
            {
                "benchmark_id": record.get("benchmark_id", ""),
                "source_type": record.get("source_type", "regression_snapshot"),
                "source_reference": record.get("source_reference", record.get("notes", "")),
                "measurement_unit": record.get("measurement_unit", record.get("unit", "")),
                "uncertainty": record.get("uncertainty", record.get("tolerance", "")),
                "validity_range": record.get("validity_range", ""),
                "confidence_level": record.get("confidence_level", "low"),
                "data_hash": record.get("data_hash") or benchmark_data_hash(record),
                "review_status": record.get("review_status", "unreviewed"),
            }
        )
    return rows


def benchmark_source_registry_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    """Return benchmark sources with release-gate confidence fields."""
    records = load_benchmark_sources(path)
    rows = []
    for row in records:
        source_type = str(row.get("source_type", "regression_snapshot"))
        confidence = row.get("confidence_level", "low")
        source_reference = str(row.get("source_reference", ""))
        validity = str(row.get("validity_range", ""))
        review_status = str(row.get("review_status", ""))
        weight = benchmark_weight_by_confidence(source_type, confidence)
        critical_allowed = bool(source_reference and "outside" not in validity.lower() and "out" not in review_status.lower())
        rows.append({**row, "weight": weight, "critical_release_allowed": critical_allowed, "passed": bool(weight > 0.0 and (source_reference or source_type == "regression_snapshot"))})
    return pd.DataFrame(rows)


def benchmark_source_registry_summary(path: str | Path | None = None) -> dict[str, Any]:
    """Return compact source-registry acceptance summary."""
    df = benchmark_source_registry_dataframe(path)
    if df.empty:
        return {"passed": False, "rows": 0, "critical_missing_source": 1}
    high_conf = df[df["source_type"].astype(str).str.lower().isin(["plant", "experiment", "literature"])]
    missing = high_conf[~high_conf["source_reference"].astype(str).str.len().gt(0)]
    failed = df[~df["passed"].astype(bool)]
    return {
        "passed": bool(missing.empty and failed.empty),
        "rows": int(len(df)),
        "critical_missing_source": int(len(missing)),
        "failed": int(len(failed)),
    }


def benchmark_lineage_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    """Return source rows normalized for report/repro lineage sheets."""
    df = benchmark_source_registry_dataframe(path)
    if df.empty:
        return df
    return df[["benchmark_id", "source_type", "source_reference", "measurement_unit", "uncertainty", "validity_range", "confidence_level", "data_hash", "review_status", "weight"]]

