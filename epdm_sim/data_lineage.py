"""Data-lineage records for benchmarks and calibration datasets.

The lineage layer is intentionally lightweight: it records provenance,
units, uncertainty and validity metadata without pulling in a database or
running any model.  Release gates can then distinguish a plant/experiment
benchmark from a low-confidence regression snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import hashlib
import json

import pandas as pd

from .experimental_benchmark import benchmark_data_hash, load_experimental_benchmarks


SOURCE_CONFIDENCE = {
    "plant": 95.0,
    "experiment": 85.0,
    "literature": 70.0,
    "synthetic": 45.0,
    "regression_snapshot": 25.0,
}


@dataclass(frozen=True)
class DataLineageRecord:
    """Provenance record for one benchmark or calibration dataset."""

    dataset_id: str
    source_type: str
    source_reference: str
    measurement_unit: str
    uncertainty: float
    validity_range: Any
    preprocessing_steps: list[str] = field(default_factory=list)
    data_hash: str = ""
    created_at: str = ""
    reviewed_by: str = "model_audit"
    confidence_level: str = "low"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["preprocessing_steps"] = "; ".join(self.preprocessing_steps)
        payload["lineage_confidence_score"] = lineage_confidence_from_record(payload)
        payload["has_source_reference"] = bool(str(self.source_reference).strip())
        return payload


def stable_data_hash(payload: Any) -> str:
    """Return a stable short hash for data-lineage payloads."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def lineage_confidence_from_record(record: dict[str, Any]) -> float:
    """Return a 0-100 lineage confidence score."""
    source = str(record.get("source_type", "regression_snapshot")).lower()
    base = SOURCE_CONFIDENCE.get(source, 25.0)
    confidence = str(record.get("confidence_level", "")).lower()
    if confidence in {"high", "plant"}:
        base += 5.0
    elif confidence == "low":
        base -= 10.0
    if not str(record.get("source_reference", "")).strip():
        base -= 15.0
    if not str(record.get("measurement_unit", "")).strip():
        base -= 10.0
    if not record.get("validity_range"):
        base -= 10.0
    return float(max(0.0, min(100.0, base)))


def build_data_lineage_record(record: dict[str, Any]) -> DataLineageRecord:
    """Build lineage metadata from one benchmark or dataset record."""
    benchmark_id = str(record.get("benchmark_id") or record.get("dataset_id") or "unnamed_dataset")
    source_type = str(record.get("source_type", "regression_snapshot"))
    source_reference = str(record.get("source_reference") or record.get("notes") or "")
    unit = str(record.get("measurement_unit") or record.get("unit") or "")
    tolerance = record.get("uncertainty", record.get("tolerance", 0.0))
    try:
        uncertainty = float(tolerance)
    except Exception:
        uncertainty = 0.0
    data_hash = str(record.get("data_hash") or benchmark_data_hash(record) if "benchmark_id" in record else stable_data_hash(record))
    return DataLineageRecord(
        dataset_id=benchmark_id,
        source_type=source_type,
        source_reference=source_reference,
        measurement_unit=unit,
        uncertainty=max(uncertainty, 0.0),
        validity_range=record.get("validity_range", "unknown"),
        preprocessing_steps=list(record.get("preprocessing_steps", ["metadata_normalized"])),
        data_hash=data_hash,
        created_at=str(record.get("created_at", "")),
        reviewed_by=str(record.get("reviewed_by", "model_audit")),
        confidence_level=str(record.get("confidence_level", "low")),
    )


def lineage_for_benchmarks(records: list[dict[str, Any]] | None = None) -> list[DataLineageRecord]:
    """Return lineage records for experimental/literature/synthetic benchmarks."""
    records = load_experimental_benchmarks() if records is None else records
    return [build_data_lineage_record(record) for record in records]


def data_lineage_dataframe(records: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    """Return benchmark/data lineage as a DataFrame."""
    return pd.DataFrame([item.as_dict() for item in lineage_for_benchmarks(records)])


def lineage_confidence_score(records: list[dict[str, Any]] | None = None) -> float:
    """Return average 0-100 lineage confidence score."""
    df = data_lineage_dataframe(records)
    if df.empty:
        return 0.0
    return float(df["lineage_confidence_score"].mean())


def critical_benchmarks_missing_lineage(records: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    """Return critical benchmark lineage failures for release gates."""
    df = data_lineage_dataframe(records)
    if df.empty:
        return pd.DataFrame(columns=["dataset_id", "passed", "reason"])
    critical_sources = {"plant", "experiment", "literature"}
    rows = []
    for _, row in df.iterrows():
        source = str(row.get("source_type", "")).lower()
        critical = source in critical_sources
        has_lineage = bool(row.get("has_source_reference")) and bool(row.get("measurement_unit")) and bool(row.get("data_hash"))
        rows.append(
            {
                "dataset_id": row.get("dataset_id"),
                "source_type": source,
                "critical": critical,
                "passed": bool((not critical) or has_lineage),
                "reason": "lineage complete" if has_lineage else "critical benchmark missing source/unit/hash lineage",
            }
        )
    return pd.DataFrame(rows)

