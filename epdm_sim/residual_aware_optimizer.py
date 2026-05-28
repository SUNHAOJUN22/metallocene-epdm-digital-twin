"""Residual-aware optimizer objective helpers for V6.2."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_aware_decision import reject_residual_critical_candidate, residual_risk_score
from .residual_objective import residual_penalty_for_optimizer
from .validity_envelope import check_value_against_range


def residual_aware_optimizer_objective(
    process_objective: float,
    result_or_system: Any,
    *,
    validity_penalty: float = 0.0,
    residual_weight: float = 1.0,
) -> dict[str, Any]:
    """Return process objective plus residual and validity penalties."""
    residual_penalty = float(residual_penalty_for_optimizer(result_or_system))
    total = float(process_objective) + float(residual_weight) * residual_penalty + max(float(validity_penalty), 0.0)
    rejected = bool(reject_residual_critical_candidate(result_or_system)["rejected"] or not np.isfinite(total))
    return {
        "process_objective": float(process_objective),
        "residual_penalty": residual_penalty,
        "validity_penalty": max(float(validity_penalty), 0.0),
        "objective": total,
        "rejected": rejected,
        "passed": not rejected,
    }


def reject_optimizer_candidate(candidate: dict[str, Any], result_or_system: Any) -> dict[str, Any]:
    """Reject optimizer candidates outside validity or with critical residuals."""
    residual = reject_residual_critical_candidate(result_or_system)
    validity_errors = []
    for variable, valid_range in {"temperature_C": (60.0, 180.0), "pressure_MPa": (0.1, 5.0)}.items():
        if variable in candidate:
            row = check_value_against_range("optimizer", variable, candidate[variable], valid_range)
            if row.status == "outside":
                validity_errors.append(variable)
    rejected = bool(residual["rejected"] or validity_errors)
    return {
        "candidate_id": candidate.get("candidate_id", "optimizer_candidate"),
        "rejected": rejected,
        "residual_rejected": bool(residual["rejected"]),
        "outside_validity": "; ".join(validity_errors),
        "residual_risk": residual_risk_score(result_or_system),
        "passed": not rejected,
    }


def residual_aware_optimizer_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return optimizer decision audit rows."""
    if result_or_system is None:
        return pd.DataFrame([{"status": "not_run", "passed": True, "rejected": False}])
    candidate = {"candidate_id": "default_optimizer_candidate", "temperature_C": 100.0, "pressure_MPa": 1.0}
    rejection = reject_optimizer_candidate(candidate, result_or_system)
    objective = residual_aware_optimizer_objective(-0.1, result_or_system)
    return pd.DataFrame([{**rejection, **objective, "status": "evaluated"}])
