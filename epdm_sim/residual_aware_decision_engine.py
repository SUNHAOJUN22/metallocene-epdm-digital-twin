"""Unified residual-aware decision engine for V6.4."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_aware_doe import residual_aware_doe_candidate_score
from .residual_aware_optimizer import reject_optimizer_candidate, residual_aware_optimizer_objective
from .residual_aware_sampling import residual_aware_sample_weight
from .residual_system import ResidualSystem
from .validity_envelope import check_value_against_range


def residual_aware_decision_engine(
    candidate: dict[str, Any] | None = None,
    result_or_system: Any | None = None,
    *,
    process_objective: float = 0.0,
    uncertainty_penalty: float = 0.0,
) -> dict[str, Any]:
    """Return one residual-aware optimizer/DOE/posterior decision."""
    system = result_or_system if result_or_system is not None else ResidualSystem()
    cand = dict(candidate or {"candidate_id": "default_v6_4_candidate", "temperature_C": 100.0, "pressure_MPa": 1.0, "hydrogen_g_h": 8.0})
    optimizer = reject_optimizer_candidate(cand, system)
    objective = residual_aware_optimizer_objective(process_objective, system, validity_penalty=max(uncertainty_penalty, 0.0), residual_weight=1.0)
    doe = residual_aware_doe_candidate_score(cand, system)
    weight = residual_aware_sample_weight(system, uncertainty_penalty=uncertainty_penalty)
    outside = []
    for variable, valid_range in {"temperature_C": (60.0, 180.0), "pressure_MPa": (0.1, 5.0)}.items():
        if variable in cand and check_value_against_range("v6_4_decision", variable, cand[variable], valid_range).status == "outside":
            outside.append(variable)
    reasons = []
    if optimizer["rejected"]:
        reasons.append("optimizer_rejected")
    if objective["rejected"]:
        reasons.append("objective_rejected")
    if doe["rejected"]:
        reasons.append("doe_rejected")
    if weight["rejected"]:
        reasons.append("posterior_residual_rejected")
    if outside:
        reasons.append("outside_validity:" + ",".join(outside))
    rejected = bool(reasons)
    risk = float(np.clip(max(float(doe.get("residual_risk", 0.0)), float(weight.get("residual_risk", 0.0)), uncertainty_penalty), 0.0, 1.0))
    return {
        "candidate_id": cand.get("candidate_id", cand.get("sample_id", "candidate")),
        "decision": "reject" if rejected else "accept",
        "rejected": rejected,
        "rejected_reason": "; ".join(reasons),
        "optimizer_objective": float(objective["objective"]),
        "doe_score": float(doe["score"]),
        "posterior_weight": 0.0 if rejected else float(weight["weight"]),
        "uncertainty_risk_probability": risk,
        "recommended": bool((not rejected) and doe.get("recommended", False)),
        "passed": not rejected,
    }


def residual_decision_engine_dataframe(
    candidates: list[dict[str, Any]] | None = None,
    result_or_system: Any | None = None,
) -> pd.DataFrame:
    """Return decision-engine audit rows."""
    candidates = candidates or [
        {"candidate_id": "h2_v6_4", "hydrogen_g_h": 8.0, "temperature_C": 100.0, "pressure_MPa": 1.5},
        {"candidate_id": "pressure_v6_4", "temperature_C": 100.0, "pressure_MPa": 1.8},
    ]
    return pd.DataFrame([residual_aware_decision_engine(candidate, result_or_system, uncertainty_penalty=float(candidate.get("uncertainty_penalty", 0.0))) for candidate in candidates])


def residual_decision_engine_gate(result_or_system: Any | None = None) -> dict[str, Any]:
    """Return release-gate status for the residual-aware decision engine."""
    df = residual_decision_engine_dataframe(result_or_system=result_or_system)
    rejected = int(df["rejected"].astype(bool).sum()) if not df.empty else 1
    bounded = bool(df["uncertainty_risk_probability"].between(0.0, 1.0).all()) if not df.empty else False
    return {"passed": bool(rejected == 0 and bounded), "rows": int(len(df)), "rejected": rejected, "bounded": bounded}

