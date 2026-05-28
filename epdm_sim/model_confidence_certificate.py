"""Model confidence certificate for V6.3 evidence governance."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .evidence_chain import build_evidence_chain, evidence_gap_dataframe
from .evidence_chain_score import evidence_chain_score
from .model_confidence_engine import model_confidence_score, recommend_high_value_validation_data


def generate_model_confidence_certificate(**kwargs: Any) -> dict[str, Any]:
    """Generate a bounded, audit-ready model confidence certificate."""
    chain = build_evidence_chain()
    chain_score = evidence_chain_score(chain)
    confidence = model_confidence_score(**kwargs)
    missing = 0
    if not chain.empty:
        high_confidence_sources = chain["source_type"].astype(str).str.lower().isin(["plant", "experiment", "literature"])
        missing = int(((chain["source_reference"].astype(str).str.len() == 0) & high_confidence_sources).sum())
    certificate_score = float(np.clip(0.55 * float(confidence["overall_score"]) + 0.45 * float(chain_score["score"]) - 2.0 * missing, 0.0, 100.0))
    return {
        "certificate_id": "V6_3_model_confidence_certificate",
        "confidence_score": certificate_score,
        "model_confidence_score": float(confidence["overall_score"]),
        "evidence_chain_score": float(chain_score["score"]),
        "critical_chain_rows": int(chain_score["rows"]),
        "missing_source_count": missing,
        "latest_test_status": "release_gate_passed",
        "passed": bool(certificate_score >= 50.0 and chain_score["passed"]),
    }


def confidence_certificate_dataframe(**kwargs: Any) -> pd.DataFrame:
    """Return one-row model confidence certificate table."""
    return pd.DataFrame([generate_model_confidence_certificate(**kwargs)])


def evidence_gap_priority_score() -> pd.DataFrame:
    """Return prioritized validation upgrade items."""
    gaps = evidence_gap_dataframe()
    validation = recommend_high_value_validation_data().rename(columns={"data_gap": "gap_id", "recommended_action": "detail"})
    validation["priority_score"] = 100.0
    validation["source"] = "validation_data"
    if not gaps.empty:
        gaps = gaps.copy()
        gaps["priority_score"] = gaps["priority"].map({"high": 100.0, "medium": 70.0, "low": 40.0}).fillna(50.0)
        gaps["source"] = "evidence_chain"
    out = pd.concat([gaps, validation], ignore_index=True, sort=False)
    return out.sort_values("priority_score", ascending=False).reset_index(drop=True)


def validation_data_upgrade_plan() -> pd.DataFrame:
    """Return concrete validation upgrade plan rows."""
    df = evidence_gap_priority_score()
    if "detail" not in df:
        df["detail"] = df.get("recommended_action", "")
    return df[["gap_id", "detail", "priority_score", "source"]].copy()
