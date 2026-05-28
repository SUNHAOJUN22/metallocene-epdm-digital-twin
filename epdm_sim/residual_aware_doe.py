"""Residual-aware DOE candidate scoring for V6.2."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .benchmark_calibration import benchmark_residual_dataframe
from .data_lineage import lineage_confidence_score
from .residual_aware_decision import reject_residual_critical_candidate, residual_risk_score
from .validity_envelope import check_value_against_range


def residual_aware_doe_candidate_score(candidate: dict[str, Any], result_or_system: Any) -> dict[str, Any]:
    """Score DOE candidate with residual, validity, lineage and benchmark signals."""
    residual_status = reject_residual_critical_candidate(result_or_system)
    risk = residual_risk_score(result_or_system)
    validity_errors = []
    for variable, valid_range in {"temperature_C": (60.0, 180.0), "pressure_MPa": (0.1, 5.0)}.items():
        if variable in candidate:
            row = check_value_against_range("doe", variable, candidate[variable], valid_range)
            if row.status == "outside":
                validity_errors.append(variable)
    lineage = lineage_confidence_score() / 100.0
    benchmark_df = benchmark_residual_dataframe({})
    benchmark_failure = int((~benchmark_df.get("passed", pd.Series(dtype=bool)).astype(bool)).sum()) if not benchmark_df.empty else 0
    h2_bonus = 0.10 if any("h2" in key.lower() or "hydrogen" in key.lower() for key in candidate) else 0.0
    pressure_bonus = 0.10 if any("pressure" in key.lower() for key in candidate) else 0.0
    score = float(np.clip(0.50 * (1.0 - risk) + 0.20 * lineage + h2_bonus + pressure_bonus - 0.10 * benchmark_failure - 0.50 * len(validity_errors), 0.0, 1.0))
    rejected = bool(residual_status["rejected"] or validity_errors)
    return {
        "candidate_id": candidate.get("candidate_id", "doe_candidate"),
        "score": 0.0 if rejected else score,
        "residual_risk": risk,
        "lineage_confidence": lineage,
        "benchmark_failures": benchmark_failure,
        "outside_validity": "; ".join(validity_errors),
        "recommended": bool((not rejected) and score >= 0.35),
        "rejected": rejected,
        "passed": not rejected,
    }


def filter_residual_aware_doe_candidates(candidates: list[dict[str, Any]], result_or_system: Any) -> pd.DataFrame:
    """Return scored DOE candidates, excluding residual-critical or outside-validity recommendations."""
    rows = [residual_aware_doe_candidate_score(candidate, result_or_system) for candidate in candidates]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["rank"] = df["score"].rank(ascending=False, method="first")
    return df


def residual_aware_doe_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return default DOE decision audit rows."""
    if result_or_system is None:
        return pd.DataFrame([{"status": "not_run", "passed": True, "recommended": False}])
    candidates = [
        {"candidate_id": "h2_screen", "hydrogen_g_h": 8.0, "pressure_MPa": 1.5, "temperature_C": 100.0},
        {"candidate_id": "pressure_screen", "pressure_MPa": 1.9, "temperature_C": 100.0},
    ]
    df = filter_residual_aware_doe_candidates(candidates, result_or_system)
    df["status"] = "evaluated"
    return df
