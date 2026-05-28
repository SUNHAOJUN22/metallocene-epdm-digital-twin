"""Evidence-chain scoring helpers for V6.2 industrial confidence gates."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .evidence_chain import build_evidence_chain, evidence_gap_dataframe, evidence_weighted_confidence, recommend_evidence_upgrade, validate_evidence_chain_completeness
from .validation_evidence import evidence_weight


def evidence_chain_score(chain: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return a bounded score from completeness and source weights."""
    chain = build_evidence_chain() if chain is None else chain
    status = validate_evidence_chain_completeness(chain)
    confidence = evidence_weighted_confidence(chain)
    if chain.empty:
        return {"score": 0.0, "passed": False, "rows": 0, "failed": 1}
    source_score = float(100.0 * pd.to_numeric(chain["source_type"].map(evidence_weight), errors="coerce").fillna(0.0).mean())
    completeness = float(100.0 * chain["passed"].astype(bool).mean())
    score = float(np.clip(0.45 * source_score + 0.35 * completeness + 0.20 * float(confidence["confidence_score"]), 0.0, 100.0))
    return {"score": score, "passed": bool(status["passed"] and score >= 40.0), "rows": int(len(chain)), "failed": int(status["failed"])}


def evidence_gap_priority_dataframe(chain: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return prioritized evidence gaps including plant mass-balance reconciliation."""
    gaps = evidence_gap_dataframe()
    extra = pd.DataFrame(
        [
            {
                "gap_id": "plant_mass_balance_reconciliation",
                "category": "plant_data",
                "detail": "plant mass balance reconciliation",
                "priority": "high",
            }
        ]
    )
    upgrades = recommend_evidence_upgrade(chain)
    if not upgrades.empty:
        upgrades = upgrades.rename(columns={"recommended_upgrade": "detail"})
        upgrades["category"] = "source_upgrade"
        upgrades["gap_id"] = upgrades.get("equation_id", pd.Series(["equation"] * len(upgrades))).astype(str) + "_source_upgrade"
    out = pd.concat([gaps, extra, upgrades[[col for col in ["gap_id", "category", "detail", "priority"] if col in upgrades.columns]] if not upgrades.empty else pd.DataFrame()], ignore_index=True)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    out["_rank"] = out["priority"].map(priority_order).fillna(9)
    return out.sort_values(["_rank", "gap_id"]).drop(columns=["_rank"]).reset_index(drop=True)


def critical_evidence_chain_gate(chain: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return release-gate status for critical evidence-chain completeness."""
    chain = build_evidence_chain() if chain is None else chain
    score = evidence_chain_score(chain)
    missing_source = 0
    if not chain.empty:
        non_low = ~chain["source_type"].isin(["synthetic", "regression_snapshot"])
        missing_source = int(((chain["source_reference"].astype(str).str.len() == 0) & non_low).sum())
    return {**score, "missing_source": missing_source, "passed": bool(score["passed"] and missing_source == 0)}


def evidence_chain_score_dataframe(chain: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return one-row evidence-chain score table."""
    return pd.DataFrame([critical_evidence_chain_gate(chain)])
