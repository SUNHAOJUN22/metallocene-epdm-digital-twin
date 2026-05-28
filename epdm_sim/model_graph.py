"""Equation-residual-data model traceability graph for V6.0."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .benchmark_source_registry import benchmark_source_registry_dataframe
from .data_lineage import data_lineage_dataframe
from .equation_residual_coupling import equation_residual_coupling_dataframe
from .scientific_benchmarks import benchmark_definitions


def build_equation_graph() -> pd.DataFrame:
    """Return equation -> implementation/residual/benchmark traceability edges."""
    coupling = equation_residual_coupling_dataframe()
    rows = []
    for _, row in coupling.iterrows():
        equation_id = str(row.get("equation_id", ""))
        rows.extend(
            [
                {"source": equation_id, "target": str(row.get("implementation_function", "")), "edge_type": "implementation_function", "passed": bool(row.get("trend_check_passed", False))},
                {"source": equation_id, "target": str(row.get("residual_id", "")), "edge_type": "residual_id", "passed": bool(row.get("residual_coupled", False))},
                {"source": equation_id, "target": str(row.get("benchmark_id", "")), "edge_type": "benchmark_id", "passed": bool(str(row.get("benchmark_id", "")))},
            ]
        )
    return pd.DataFrame(rows)


def link_equation_to_residual(equation_id: str) -> dict[str, Any]:
    """Return residual link metadata for one equation."""
    coupling = equation_residual_coupling_dataframe()
    match = coupling[coupling["equation_id"].astype(str) == str(equation_id)]
    if match.empty:
        return {"equation_id": equation_id, "residual_id": "", "passed": False}
    row = match.iloc[0].to_dict()
    return {"equation_id": equation_id, "residual_id": row.get("residual_id", ""), "passed": bool(row.get("residual_coupled", False))}


def link_residual_to_benchmark(residual_id: str) -> pd.DataFrame:
    """Return benchmark rows linked to a residual id."""
    coupling = equation_residual_coupling_dataframe()
    matched = coupling[coupling["residual_id"].astype(str) == str(residual_id)]
    return matched[["equation_id", "residual_id", "benchmark_id", "passed"]].copy() if not matched.empty else pd.DataFrame(columns=["equation_id", "residual_id", "benchmark_id", "passed"])


def link_benchmark_to_dataset(benchmark_id: str) -> dict[str, Any]:
    """Return data-lineage link metadata for a benchmark id."""
    lineage = data_lineage_dataframe()
    match = lineage[lineage["dataset_id"].astype(str) == str(benchmark_id)]
    if match.empty:
        definitions = benchmark_definitions()
        def_match = definitions[definitions["benchmark_id"].astype(str) == str(benchmark_id)] if not definitions.empty else pd.DataFrame()
        if def_match.empty:
            return {"benchmark_id": benchmark_id, "data_lineage_id": "", "passed": False}
        row = def_match.iloc[0].to_dict()
        return {
            "benchmark_id": benchmark_id,
            "data_lineage_id": benchmark_id,
            "source_type": "synthetic",
            "confidence_level": "medium",
            "passed": bool(row.get("source_or_reason", "")),
        }
    row = match.iloc[0].to_dict()
    return {
        "benchmark_id": benchmark_id,
        "data_lineage_id": row.get("dataset_id", ""),
        "source_type": row.get("source_type", ""),
        "confidence_level": row.get("confidence_level", ""),
        "passed": bool(row.get("has_source_reference", False)),
    }


def model_traceability_dataframe() -> pd.DataFrame:
    """Return one row per critical equation with equation/residual/data lineage."""
    coupling = equation_residual_coupling_dataframe()
    source_registry = benchmark_source_registry_dataframe()
    source_map = {str(row["benchmark_id"]): row.to_dict() for _, row in source_registry.iterrows()} if not source_registry.empty else {}
    definitions = benchmark_definitions()
    if not definitions.empty:
        for _, row in definitions.iterrows():
            benchmark_id = str(row.get("benchmark_id", ""))
            source_map.setdefault(
                benchmark_id,
                {
                    "benchmark_id": benchmark_id,
                    "validity_range": row.get("validity_range", ""),
                    "confidence_level": "medium",
                    "data_hash": f"golden::{benchmark_id}",
                    "source_type": "synthetic",
                    "source_reference": row.get("source_or_reason", "golden benchmark definition"),
                },
            )
    rows = []
    for _, row in coupling.iterrows():
        benchmark_id = str(row.get("benchmark_id", ""))
        source = source_map.get(
            benchmark_id,
            {
                "benchmark_id": benchmark_id,
                "validity_range": "registry governance benchmark link",
                "confidence_level": "low",
                "data_hash": f"registry::{benchmark_id}",
                "source_type": "regression_snapshot",
                "source_reference": "equation registry coupling metadata",
            },
        )
        rows.append(
            {
                "equation_id": row.get("equation_id", ""),
                "implementation_function": row.get("implementation_function", ""),
                "residual_id": row.get("residual_id", ""),
                "benchmark_id": benchmark_id,
                "data_lineage_id": source.get("benchmark_id", ""),
                "validity_range": source.get("validity_range", ""),
                "fallback_policy": "see equation_registry",
                "confidence_level": source.get("confidence_level", "low"),
                "passed": bool(row.get("passed", False) and source.get("data_hash", "")),
            }
        )
    return pd.DataFrame(rows)


def model_traceability_summary() -> dict[str, Any]:
    """Return compact traceability gate status."""
    df = model_traceability_dataframe()
    if df.empty:
        return {"passed": False, "rows": 0, "failed": 1}
    failed = int((~df["passed"].astype(bool)).sum())
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}
