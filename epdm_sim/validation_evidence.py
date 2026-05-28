"""Evidence tables for model validation and audit confidence."""

from __future__ import annotations

import pandas as pd

from .benchmark_calibration import benchmark_weight_by_confidence
from .benchmark_source_registry import benchmark_source_registry_dataframe
from .data_lineage import data_lineage_dataframe


def evidence_weight(source_type: str) -> float:
    """Return source-type evidence weight with plant as strongest evidence."""
    return {"plant": 1.0, "experiment": 0.85, "literature": 0.7, "synthetic": 0.45, "regression_snapshot": 0.25}.get(str(source_type).lower(), 0.25)


def validation_evidence_dataframe() -> pd.DataFrame:
    """Return benchmark/data-lineage evidence rows."""
    sources = benchmark_source_registry_dataframe()
    lineage = data_lineage_dataframe()
    lineage_map = {str(row["dataset_id"]): row.to_dict() for _, row in lineage.iterrows()} if not lineage.empty else {}
    rows = []
    for _, row in sources.iterrows():
        benchmark_id = str(row.get("benchmark_id", ""))
        line = lineage_map.get(benchmark_id, {})
        source_type = str(row.get("source_type", "regression_snapshot"))
        confidence = row.get("confidence_level", "low")
        rows.append(
            {
                "benchmark_id": benchmark_id,
                "source_type": source_type,
                "source_reference": row.get("source_reference", ""),
                "confidence_level": confidence,
                "evidence_weight": benchmark_weight_by_confidence(source_type, confidence),
                "lineage_score": line.get("lineage_confidence_score", 0.0),
                "passed": bool(row.get("passed", False) and line.get("data_hash", "")),
            }
        )
    return pd.DataFrame(rows)
