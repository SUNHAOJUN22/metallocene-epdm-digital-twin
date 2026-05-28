"""Residual-aware posterior, uncertainty and DOE decision helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .benchmark_calibration import benchmark_residual_dataframe
from .data_lineage import lineage_confidence_score
from .posterior_residual_filter import residual_penalty_for_sample
from .residual_system import ResidualSystem, residual_system_acceptance


def reject_residual_critical_candidate(result_or_system: Any) -> dict[str, Any]:
    """Return rejection status for a residual critical candidate."""
    system = result_or_system if isinstance(result_or_system, ResidualSystem) else getattr(result_or_system, "residual_system", None)
    if not isinstance(system, ResidualSystem):
        from .residual_system import build_flowsheet_residual_system

        system = build_flowsheet_residual_system(result_or_system)
    acc = residual_system_acceptance(system)
    rejected = bool(acc["critical_count"] > 0 or not acc["passed"])
    return {**acc, "rejected": rejected}


def residual_risk_score(result_or_system: Any) -> float:
    """Return a bounded residual risk score in [0, 1]."""
    status = reject_residual_critical_candidate(result_or_system)
    score = 1.0 - float(status["overall_score"]) / 100.0
    score += 0.25 * float(status["critical_count"])
    return float(np.clip(score, 0.0, 1.0))


def residual_aware_doe_score(candidate: dict[str, float], result_or_system: Any) -> dict[str, Any]:
    """Score a DOE candidate from residual risk, validity edge and lineage confidence."""
    risk = residual_risk_score(result_or_system)
    lineage = lineage_confidence_score() / 100.0
    h2_bonus = 0.10 if "h2" in " ".join(candidate.keys()).lower() else 0.0
    pressure_bonus = 0.10 if any("pressure" in key.lower() for key in candidate) else 0.0
    feasibility = float(np.clip(1.0 - risk, 0.0, 1.0))
    score = float(np.clip(0.55 * feasibility + 0.25 * lineage + h2_bonus + pressure_bonus, 0.0, 1.0))
    return {
        "candidate_id": candidate.get("candidate_id", "candidate"),
        "residual_risk": risk,
        "lineage_confidence": lineage,
        "residual_aware_score": score,
        "recommended": bool(score >= 0.45 and risk < 1.0),
    }


def residual_aware_posterior_weight(sample: dict[str, float], result_or_system: Any) -> dict[str, Any]:
    """Return posterior sample weight after residual and parameter penalties."""
    penalty = residual_penalty_for_sample(sample, result_or_system)
    weight = float(np.exp(-min(penalty, 700.0) / 100.0))
    rejected = bool(reject_residual_critical_candidate(result_or_system)["rejected"] or penalty >= 1000.0)
    return {"residual_penalty": float(penalty), "posterior_weight": 0.0 if rejected else weight, "rejected": rejected}


def residual_aware_uncertainty_risk(base_probability: float, result_or_system: Any) -> dict[str, Any]:
    """Combine base risk probability with residual risk while keeping [0, 1]."""
    base = float(np.clip(base_probability, 0.0, 1.0))
    residual = residual_risk_score(result_or_system)
    probability = float(np.clip(base + (1.0 - base) * residual, 0.0, 1.0))
    return {"base_probability": base, "residual_risk": residual, "risk_probability": probability}


def residual_aware_decision_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return a report-safe audit table for residual-aware decisions."""
    if result_or_system is None:
        return pd.DataFrame([{"status": "not_run", "recommended": False, "risk_probability": 0.0}])
    candidate = {"candidate_id": "default_residual_aware_doe", "H2_kg_h": 0.02, "pressure_MPa": 1.8}
    doe = residual_aware_doe_score(candidate, result_or_system)
    posterior = residual_aware_posterior_weight({"k_h2_transfer": 1.0, "pressure_factor": 1.0}, result_or_system)
    uncertainty = residual_aware_uncertainty_risk(0.05, result_or_system)
    benchmark_failures = int((benchmark_residual_dataframe({}).get("passed", pd.Series(dtype=bool)).astype(bool) == False).sum()) if not benchmark_residual_dataframe({}).empty else 0
    return pd.DataFrame([{**doe, **posterior, **uncertainty, "benchmark_failures": benchmark_failures, "status": "evaluated"}])
