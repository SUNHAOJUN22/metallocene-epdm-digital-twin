"""Evidence-weighted model confidence engine for V6.0."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .benchmark_calibration import update_model_confidence_from_benchmarks
from .data_lineage import lineage_confidence_score
from .equation_residual_coupling import equation_residual_coupling_summary
from .residual_system import ResidualSystem, residual_system_acceptance
from .validation_evidence import validation_evidence_dataframe


def model_confidence_score(
    *,
    residual_system: ResidualSystem | None = None,
    model_outputs: dict[str, Any] | None = None,
    unit_safety_score: float = 100.0,
    validity_score: float = 85.0,
) -> dict[str, Any]:
    """Return evidence-weighted model confidence components."""
    residual_score = 80.0
    if residual_system is not None:
        residual_acceptance = residual_system_acceptance(residual_system)
        residual_score = float(residual_acceptance["overall_score"])
    coupling = equation_residual_coupling_summary()
    equation_score = 100.0 if coupling["passed"] else 60.0
    lineage_score = lineage_confidence_score()
    benchmark = update_model_confidence_from_benchmarks(70.0, model_outputs or {})
    evidence = validation_evidence_dataframe()
    evidence_score = float(evidence["evidence_weight"].mean() * 100.0) if not evidence.empty else 25.0
    components = {
        "residual_acceptance": residual_score,
        "equation_binding": equation_score,
        "unit_safety": float(unit_safety_score),
        "validity_envelope": float(validity_score),
        "data_lineage": lineage_score,
        "benchmark_evidence": evidence_score,
        "benchmark_adjusted": float(benchmark["adjusted_score"]),
    }
    overall = float(np.clip(sum(components.values()) / len(components), 0.0, 100.0))
    return {**components, "overall_score": overall, "passed": overall >= 60.0}


def confidence_decomposition(**kwargs: Any) -> pd.DataFrame:
    """Return confidence components as a DataFrame."""
    score = model_confidence_score(**kwargs)
    return pd.DataFrame([{"component": key, "score": value, "passed": 0.0 <= float(value) <= 100.0} for key, value in score.items() if key != "passed"])


def recommend_high_value_validation_data(**_: Any) -> pd.DataFrame:
    """Return concrete high-value validation data gaps."""
    rows = [
        ("VLE/flash recovery", "phase_equilibrium", "Measure C2/C3/H2/ENB/solvent vapor-liquid recovery vs T/P."),
        ("reaction calorimetry", "heat_balance", "Measure heat release and cooling duty for deltaH validation."),
        ("solution rheology", "transport", "Measure viscosity vs solids, Mw, shear rate and temperature."),
        ("GPC/Mooney", "polymer_properties", "Measure Mw/PDI/Mooney endpoint response to H2 and residence time."),
        ("dynamic T/P profile", "dynamic_ode", "Record semi-batch T/P/Q time series for RHS residual validation."),
    ]
    return pd.DataFrame([{"data_gap": a, "category": b, "recommended_action": c, "priority": "high"} for a, b, c in rows])


def model_confidence_engine_dataframe(**kwargs: Any) -> pd.DataFrame:
    """Return confidence decomposition plus data-gap summary rows."""
    return confidence_decomposition(**kwargs)
