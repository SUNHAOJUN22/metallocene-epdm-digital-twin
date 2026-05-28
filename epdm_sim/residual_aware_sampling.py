"""Residual-aware sampling decisions for V6.3 posterior/DOE/optimizer paths."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_aware_doe import residual_aware_doe_candidate_score
from .residual_aware_optimizer import residual_aware_optimizer_objective, reject_optimizer_candidate
from .residual_system import ResidualSystem, residual_system_acceptance


def residual_aware_sample_weight(
    result_or_system: Any,
    *,
    prior_weight: float = 1.0,
    uncertainty_penalty: float = 0.0,
) -> dict[str, Any]:
    """Return bounded sample weight after residual and uncertainty penalties."""
    status = residual_system_acceptance(result_or_system if isinstance(result_or_system, ResidualSystem) else ResidualSystem())
    risk = 1.0 - float(status["overall_score"]) / 100.0
    rejected = bool(status["critical_count"] > 0)
    weight = 0.0 if rejected else float(np.clip(float(prior_weight) * (1.0 - risk) - max(float(uncertainty_penalty), 0.0), 0.0, 1.0))
    return {"weight": weight, "residual_risk": risk, "rejected": rejected, "passed": not rejected}


def residual_aware_sampling_decision(
    sample: dict[str, Any],
    result_or_system: Any,
    *,
    uncertainty_penalty: float = 0.0,
) -> dict[str, Any]:
    """Return one residual-aware sampling decision."""
    candidate = reject_optimizer_candidate(sample, result_or_system)
    doe = residual_aware_doe_candidate_score(sample, result_or_system)
    objective = residual_aware_optimizer_objective(float(sample.get("process_objective", 0.0)), result_or_system, validity_penalty=0.0, residual_weight=1.0)
    weight = residual_aware_sample_weight(result_or_system, uncertainty_penalty=uncertainty_penalty)
    rejected = bool(candidate["rejected"] or doe["rejected"] or objective["rejected"] or weight["rejected"])
    return {
        "sample_id": sample.get("sample_id", sample.get("candidate_id", "sample")),
        "optimizer_rejected": bool(candidate["rejected"]),
        "doe_rejected": bool(doe["rejected"]),
        "posterior_weight": 0.0 if rejected else weight["weight"],
        "uncertainty_risk_probability": float(np.clip(sample.get("uncertainty_risk_probability", uncertainty_penalty), 0.0, 1.0)),
        "recommended": bool((not rejected) and doe["recommended"]),
        "rejected": rejected,
        "passed": not rejected,
    }


def residual_aware_sampling_dataframe(
    samples: list[dict[str, Any]] | None = None,
    result_or_system: Any | None = None,
) -> pd.DataFrame:
    """Return residual-aware sampling audit table."""
    system = result_or_system if result_or_system is not None else ResidualSystem()
    samples = samples or [
        {"sample_id": "h2_screen", "hydrogen_g_h": 8.0, "pressure_MPa": 1.5, "temperature_C": 100.0, "uncertainty_risk_probability": 0.1},
        {"sample_id": "pressure_screen", "pressure_MPa": 1.8, "temperature_C": 100.0, "uncertainty_risk_probability": 0.2},
    ]
    return pd.DataFrame([residual_aware_sampling_decision(sample, system, uncertainty_penalty=float(sample.get("uncertainty_risk_probability", 0.0))) for sample in samples])

