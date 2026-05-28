"""Data-lineage graph helpers for benchmarks and calibration datasets."""

from __future__ import annotations

import pandas as pd

from .benchmark_source_registry import benchmark_source_registry_dataframe
from .data_lineage import data_lineage_dataframe


def build_data_lineage_graph() -> pd.DataFrame:
    """Return benchmark -> source/data hash lineage edges."""
    lineage = data_lineage_dataframe()
    rows = []
    for _, row in lineage.iterrows():
        dataset_id = str(row.get("dataset_id", ""))
        rows.extend(
            [
                {"source": dataset_id, "target": row.get("source_type", ""), "edge_type": "source_type", "passed": bool(row.get("source_type", ""))},
                {"source": dataset_id, "target": row.get("data_hash", ""), "edge_type": "data_hash", "passed": bool(row.get("data_hash", ""))},
                {"source": dataset_id, "target": row.get("measurement_unit", ""), "edge_type": "measurement_unit", "passed": bool(row.get("measurement_unit", ""))},
            ]
        )
    return pd.DataFrame(rows)


def data_lineage_graph_summary() -> dict[str, int | bool]:
    """Return compact data-lineage graph status."""
    graph = build_data_lineage_graph()
    registry = benchmark_source_registry_dataframe()
    failed = int((~graph["passed"].astype(bool)).sum()) if not graph.empty else 1
    critical_missing = 0
    if not registry.empty:
        critical = registry[registry["source_type"].astype(str).str.lower().isin(["plant", "experiment", "literature"])]
        critical_missing = int((~critical["source_reference"].astype(str).str.len().gt(0)).sum())
    return {"passed": failed == 0 and critical_missing == 0, "edges": int(len(graph)), "failed": failed, "critical_missing_source": critical_missing}
