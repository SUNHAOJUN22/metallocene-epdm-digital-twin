"""Closed-loop calibration, identifiability, uncertainty and DOE helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .doe_optimal import recommend_optimal_doe
from .flowsheet import ProcessConfig, load_default_config
from .identifiability import IdentifiabilityResult, evaluate_identifiability
from .parameter_estimation import default_estimation_parameters
from .uncertainty import UncertaintyResult, run_uncertainty_analysis
from .utils import clamp, model_dump_compat


@dataclass
class CalibrationLoopResult:
    """One closed-loop calibration and experimental-design summary."""

    current_parameter_set: dict[str, Any]
    fitted_metrics: pd.DataFrame
    identifiability_summary: pd.DataFrame
    uncertainty_summary: pd.DataFrame
    recommended_experiments: pd.DataFrame
    expected_information_gain: pd.DataFrame
    expected_risk_reduction: pd.DataFrame
    warnings: list[str] = field(default_factory=list)

    def as_dataframe(self) -> pd.DataFrame:
        """Return a compact loop status table."""
        return pd.DataFrame(
            [
                {"section": "parameters", "rows": len(self.current_parameter_set), "warnings": ""},
                {"section": "identifiability", "rows": len(self.identifiability_summary), "warnings": "; ".join(self.warnings)},
                {"section": "uncertainty", "rows": len(self.uncertainty_summary), "warnings": ""},
                {"section": "recommended_experiments", "rows": len(self.recommended_experiments), "warnings": ""},
            ]
        )


def rank_parameters_by_uncertainty(identifiability: IdentifiabilityResult, uncertainty: UncertaintyResult | None = None) -> pd.DataFrame:
    """Rank parameters by weak identifiability and KPI uncertainty leverage."""
    status = identifiability.status.copy()
    status["identifiability_penalty"] = status["status"].map({"identifiable": 0.0, "weakly_identifiable": 1.0, "not_identifiable": 2.0}).fillna(1.0)
    kpi_spread = 0.0
    if uncertainty is not None and not uncertainty.confidence_intervals.empty:
        ci = uncertainty.confidence_intervals
        spread = (ci["p95"] - ci["p05"]).abs() / ci["p50"].abs().clip(lower=1.0e-9)
        kpi_spread = float(spread.replace([np.inf, -np.inf], np.nan).fillna(0.0).mean())
    status["uncertainty_leverage"] = kpi_spread
    status["priority_score"] = status["identifiability_penalty"] * 10.0 + status["uncertainty_leverage"]
    return status.sort_values("priority_score", ascending=False).reset_index(drop=True)


def recommend_experiments_for_weak_parameters(
    weak_parameters: list[str],
    base_config: ProcessConfig | None = None,
) -> pd.DataFrame:
    """Return targeted experiments for weak parameter classes."""
    cfg = base_config or load_default_config()
    base = model_dump_compat(cfg)
    rows: list[dict[str, Any]] = []

    def add(label: str, reason: str, **updates: Any) -> None:
        payload = dict(base)
        payload.update(updates)
        rows.append({"experiment_id": label, "reason": reason, **updates, "config": str(payload)})

    if "beta_P" in weak_parameters:
        for pressure in [0.7, 1.0, 2.0]:
            add(f"pressure_gradient_{pressure:g}MPa", "beta_P 需要压力梯度以识别ENB压力抑制项", pressure_MPa=pressure)
    if "beta_E" in weak_parameters:
        add("E_ENB_low_E", "beta_E 需要 C_E/C_ENB 梯度；低乙烯高ENB点增强竞争项辨识", ethylene_kg_h=base["ethylene_kg_h"] * 0.75, enb_kg_h=base["enb_kg_h"] * 1.4)
        add("E_ENB_high_E", "beta_E 需要 C_E/C_ENB 梯度；高乙烯低ENB点增强竞争项辨识", ethylene_kg_h=base["ethylene_kg_h"] * 1.25, enb_kg_h=base["enb_kg_h"] * 0.8)
    if "ktr_H2" in weak_parameters:
        for h2 in [0.0, max(base["hydrogen_g_h"], 1.0), base["hydrogen_g_h"] * 3.0]:
            add(f"H2_gradient_{h2:.1f}g_h", "ktr_H2 需要H2梯度以识别链转移项", hydrogen_g_h=h2)
    if "kd_h" in weak_parameters:
        for tau in [base["residence_time_min"] * 0.5, base["residence_time_min"], base["residence_time_min"] * 1.8]:
            add(f"tau_gradient_{tau:.0f}min", "kd_h 需要时间/停留时间梯度或动态时间序列", residence_time_min=tau)
    if not rows:
        add("repeat_center_point", "当前参数可辨识性较好，建议重复中心点估计实验误差", pressure_MPa=base["pressure_MPa"])
    return pd.DataFrame(rows)


def estimate_information_gain(candidate_experiments: pd.DataFrame, weak_parameters: list[str]) -> pd.DataFrame:
    """Estimate relative information gain for candidate experiments."""
    if candidate_experiments.empty:
        return pd.DataFrame(columns=["experiment_id", "expected_information_gain", "covered_parameters"])
    rows = []
    for _, row in candidate_experiments.iterrows():
        reason = str(row.get("reason", ""))
        covered = [param for param in weak_parameters if param in reason or _parameter_hint(param) in reason]
        if not covered:
            covered = weak_parameters[:1]
        gain = clamp(20.0 + 18.0 * len(covered), 0.0, 100.0)
        rows.append({"experiment_id": row.get("experiment_id"), "expected_information_gain": gain, "covered_parameters": ", ".join(covered)})
    return pd.DataFrame(rows)


def _parameter_hint(parameter: str) -> str:
    return {"beta_P": "压力", "beta_E": "C_E/C_ENB", "ktr_H2": "H2", "kd_h": "停留时间"}.get(parameter, parameter)


def run_calibration_loop(
    dataset: pd.DataFrame | None = None,
    parameter_set: dict[str, Any] | None = None,
    config: ProcessConfig | dict[str, Any] | None = None,
    target_metrics: list[str] | None = None,
) -> CalibrationLoopResult:
    """Run the lightweight calibration loop without triggering ODE/CFD/optimizer."""
    cfg = config if isinstance(config, ProcessConfig) else ProcessConfig(**(config or model_dump_compat(load_default_config())))
    params = parameter_set or default_estimation_parameters()
    warnings: list[str] = []
    ident = evaluate_identifiability(dataset, cfg)
    uncertainty = run_uncertainty_analysis(cfg, n_samples=8, seed=11)
    ranked = rank_parameters_by_uncertainty(ident, uncertainty)
    weak = ranked.loc[ranked["status"] != "identifiable", "parameter"].astype(str).tolist()
    if not weak:
        weak = ["beta_P", "ktr_H2"]
        warnings.append("No weak parameters detected by proxy; recommending pressure and H2 confirmation experiments.")
    targeted = recommend_experiments_for_weak_parameters(weak, cfg)
    feasible = recommend_optimal_doe(cfg, max_experiments=6).recommendations
    recommendations = pd.concat([targeted, feasible], ignore_index=True, sort=False).drop_duplicates(subset=["experiment_id"], keep="first")
    gain = estimate_information_gain(recommendations, weak)
    risk_reduction = pd.DataFrame(
        [
            {"risk": "cooling_margin_lt_0", "current_probability": uncertainty.risk_probabilities.get("probability_cooling_margin_lt_0", 0.0), "expected_risk_reduction": 0.15},
            {"risk": "fouling_index_gt_3", "current_probability": uncertainty.risk_probabilities.get("probability_fouling_index_gt_3", 0.0), "expected_risk_reduction": 0.10},
        ]
    )
    metrics = pd.DataFrame(
        [
            {"metric": metric, "status": "tracked", "source": "target_metrics"}
            for metric in (target_metrics or ["C2_wt", "ENB_wt", "Mooney", "Mw", "activity"])
        ]
    )
    return CalibrationLoopResult(
        current_parameter_set=dict(params),
        fitted_metrics=metrics,
        identifiability_summary=ident.status,
        uncertainty_summary=uncertainty.confidence_intervals,
        recommended_experiments=recommendations,
        expected_information_gain=gain,
        expected_risk_reduction=risk_reduction,
        warnings=warnings + ident.warnings,
    )
