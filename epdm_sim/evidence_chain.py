"""Industrial evidence-chain governance for equation/residual/data lineage."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .benchmark_source_registry import benchmark_source_registry_dataframe
from .data_lineage_graph import build_data_lineage_graph
from .model_graph import model_traceability_dataframe
from .validation_evidence import evidence_weight, validation_evidence_dataframe


def build_evidence_chain() -> pd.DataFrame:
    """Join traceability, source registry and data lineage into one audit chain."""
    trace = model_traceability_dataframe()
    sources = benchmark_source_registry_dataframe()
    source_map = {str(row["benchmark_id"]): row.to_dict() for _, row in sources.iterrows()} if not sources.empty else {}
    lineage = build_data_lineage_graph()
    lineage_ids = set(lineage.get("target", pd.Series(dtype=str)).astype(str)) if not lineage.empty else set()
    rows: list[dict[str, Any]] = []
    for _, row in trace.iterrows():
        benchmark_id = str(row.get("benchmark_id", ""))
        source = source_map.get(benchmark_id, {})
        source_type = str(source.get("source_type", row.get("source_type", "regression_snapshot")))
        source_reference = str(source.get("source_reference", row.get("source_reference", "")))
        confidence_level = str(source.get("confidence_level", row.get("confidence_level", "low")))
        data_lineage_id = str(row.get("data_lineage_id", benchmark_id))
        weight = evidence_weight(source_type)
        complete = bool(row.get("residual_id", "") and benchmark_id and data_lineage_id and (source_reference or source_type in {"synthetic", "regression_snapshot"}))
        rows.append(
            {
                "equation_id": row.get("equation_id", ""),
                "implementation_function": row.get("implementation_function", ""),
                "residual_id": row.get("residual_id", ""),
                "benchmark_id": benchmark_id,
                "data_lineage_id": data_lineage_id,
                "lineage_graph_linked": data_lineage_id in lineage_ids or benchmark_id in lineage_ids,
                "source_type": source_type,
                "source_reference": source_reference,
                "confidence_level": confidence_level,
                "evidence_weight": weight,
                "complete": complete,
                "passed": complete and weight > 0.0,
            }
        )
    return pd.DataFrame(rows)


def evidence_gap_dataframe() -> pd.DataFrame:
    """Return missing evidence plus high-value experimental data gaps."""
    chain = build_evidence_chain()
    gaps: list[dict[str, Any]] = []
    if not chain.empty:
        for _, row in chain[~chain["passed"].astype(bool)].iterrows():
            gaps.append(
                {
                    "gap_id": f"chain_gap_{row.get('equation_id', 'unknown')}",
                    "category": "traceability",
                    "detail": f"Missing evidence chain for {row.get('equation_id', '')}",
                    "priority": "high",
                }
            )
    for gap, category in [
        ("VLE/flash recovery", "phase_equilibrium"),
        ("reaction calorimetry", "heat_balance"),
        ("solution rheology", "transport"),
        ("GPC/Mooney", "polymer_properties"),
        ("dynamic T/P profile", "dynamic_ode"),
    ]:
        gaps.append({"gap_id": gap.lower().replace("/", "_").replace(" ", "_"), "category": category, "detail": gap, "priority": "medium"})
    return pd.DataFrame(gaps)


def validate_evidence_chain_completeness(chain: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return compact evidence-chain completeness status."""
    chain = build_evidence_chain() if chain is None else chain
    if chain.empty:
        return {"passed": False, "rows": 0, "failed": 1, "mean_weight": 0.0}
    failed = int((~chain["passed"].astype(bool)).sum())
    mean_weight = float(pd.to_numeric(chain["evidence_weight"], errors="coerce").fillna(0.0).mean())
    return {"passed": failed == 0 and mean_weight > 0.0, "rows": int(len(chain)), "failed": failed, "mean_weight": mean_weight}


def evidence_weighted_confidence(chain: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return an evidence-weighted confidence score in [0, 100]."""
    chain = build_evidence_chain() if chain is None else chain
    if chain.empty:
        return {"confidence_score": 0.0, "passed": False}
    weights = pd.to_numeric(chain["evidence_weight"], errors="coerce").fillna(0.0)
    completeness = chain["passed"].astype(bool).astype(float)
    score = float(np.clip(100.0 * (0.70 * weights.mean() + 0.30 * completeness.mean()), 0.0, 100.0))
    return {"confidence_score": score, "passed": score >= 40.0}


def recommend_evidence_upgrade(chain: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return concrete evidence-upgrade recommendations."""
    chain = build_evidence_chain() if chain is None else chain
    evidence = validation_evidence_dataframe()
    rows = []
    low_conf = chain[chain["evidence_weight"] <= 0.45] if not chain.empty else pd.DataFrame()
    for _, row in low_conf.head(10).iterrows():
        rows.append(
            {
                "equation_id": row.get("equation_id", ""),
                "benchmark_id": row.get("benchmark_id", ""),
                "recommended_upgrade": "Replace synthetic/regression evidence with experiment, literature, or plant data.",
                "priority": "high" if row.get("source_type") == "regression_snapshot" else "medium",
            }
        )
    if not evidence.empty and not rows:
        rows.append({"equation_id": "all", "benchmark_id": "all", "recommended_upgrade": "Maintain source review cadence and add plant historian links.", "priority": "medium"})
    return pd.DataFrame(rows)
