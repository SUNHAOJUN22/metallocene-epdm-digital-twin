"""Model-governance certificate tables for V6.4 UI/report paths."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .evidence_chain_score import evidence_chain_score_dataframe, evidence_gap_priority_dataframe
from .model_confidence_certificate import confidence_certificate_dataframe
from .property_runtime_audit import property_runtime_audit_dataframe
from .residual_aware_decision_engine import residual_decision_engine_dataframe
from .residual_system import build_flowsheet_residual_system


def governance_certificate_dataframe(result: Any | None = None) -> pd.DataFrame:
    """Return a compact governance certificate for UI and report use."""
    system = build_flowsheet_residual_system(result) if result is not None else None
    confidence = confidence_certificate_dataframe(residual_system=system, model_outputs=getattr(result, "kpis", {}) if result is not None else None)
    evidence = evidence_chain_score_dataframe()
    property_audit = property_runtime_audit_dataframe(result)
    decision = residual_decision_engine_dataframe(result_or_system=system)
    rows = [
        {
            "section": "confidence_certificate",
            "score": float(confidence.get("confidence_score", pd.Series([0.0])).iloc[0]) if not confidence.empty else 0.0,
            "passed": bool(confidence.get("passed", pd.Series([False])).iloc[0]) if not confidence.empty else False,
            "detail": "model confidence certificate",
        },
        {
            "section": "evidence_chain",
            "score": float(evidence.get("score", pd.Series([0.0])).iloc[0]) if not evidence.empty else 0.0,
            "passed": bool(evidence.get("passed", pd.Series([False])).iloc[0]) if not evidence.empty else False,
            "detail": "equation-residual-benchmark-lineage confidence",
        },
        {
            "section": "property_runtime_audit",
            "score": float(property_audit.get("residual_score", pd.Series([100.0])).mean()) if not property_audit.empty else 100.0,
            "passed": bool(property_audit.get("passed", pd.Series([False])).astype(bool).all()) if not property_audit.empty else False,
            "detail": "calibrated/default property runtime status",
        },
        {
            "section": "residual_decision_engine",
            "score": 100.0 * (1.0 - float(decision.get("uncertainty_risk_probability", pd.Series([0.0])).mean())) if not decision.empty else 0.0,
            "passed": bool(decision.get("passed", pd.Series([False])).astype(bool).all()) if not decision.empty else False,
            "detail": "optimizer/DOE/posterior residual decision status",
        },
    ]
    gaps = evidence_gap_priority_dataframe()
    rows.append(
        {
            "section": "validation_gap_priority",
            "score": 100.0 - min(float(len(gaps)) * 5.0, 100.0),
            "passed": not gaps.empty,
            "detail": "; ".join(gaps.get("gap_id", pd.Series(dtype=str)).astype(str).head(5)),
        }
    )
    return pd.DataFrame(rows)


def governance_certificate_summary(result: Any | None = None) -> dict[str, Any]:
    """Return compact model-governance certificate status."""
    df = governance_certificate_dataframe(result)
    passed = bool(not df.empty and df["passed"].astype(bool).all())
    score = float(pd.to_numeric(df.get("score", pd.Series([0.0])), errors="coerce").fillna(0.0).mean())
    return {"passed": passed, "rows": int(len(df)), "score": score}


def governance_certificate_gate(result: Any | None = None) -> dict[str, Any]:
    """Return release-gate status for governance certificate data."""
    return governance_certificate_summary(result)

