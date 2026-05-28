"""Uncertainty-driven constrained DOE ranking utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, run_flowsheet
from .preflight import run_preflight_for_flowsheet
from .residual_objective import residual_penalty_for_optimizer
from .residual_system import build_flowsheet_residual_system, residual_system_acceptance
from .utils import model_dump_compat


@dataclass(frozen=True)
class CandidateExperiment:
    """One ranked candidate experiment."""

    config: dict[str, Any]
    expected_information_gain: float
    expected_uncertainty_reduction: float
    predicted_risk: float
    feasibility_flags: dict[str, bool]
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        row = dict(self.config)
        row.update(
            {
                "expected_information_gain": self.expected_information_gain,
                "expected_uncertainty_reduction": self.expected_uncertainty_reduction,
                "predicted_risk": self.predicted_risk,
                "rationale": self.rationale,
            }
        )
        row.update({f"feasible_{k}": v for k, v in self.feasibility_flags.items()})
        return row


def generate_candidate_design_space(template_id: str, base_config: ProcessConfig, ranges: dict[str, list[float]] | None = None) -> list[ProcessConfig]:
    """Generate a compact deterministic candidate design space."""
    ranges = ranges or {
        "pressure_MPa": [0.7, 1.0, 2.0],
        "hydrogen_g_h": [max(base_config.hydrogen_g_h * 0.2, 0.1), base_config.hydrogen_g_h, max(base_config.hydrogen_g_h * 5.0, 15.0)],
        "enb_kg_h": [max(base_config.enb_kg_h * 0.6, 0.1), base_config.enb_kg_h, max(base_config.enb_kg_h * 1.8, 1.0)],
        "temperature_C": [max(base_config.temperature_C - 15.0, 70.0), base_config.temperature_C, min(base_config.temperature_C + 20.0, 150.0)],
    }
    candidates: list[ProcessConfig] = []
    for key, values in ranges.items():
        for value in values:
            cfg = base_config.model_copy(deep=True)
            setattr(cfg, key, value)
            candidates.append(cfg)
    # Add E/ENB contrast points for beta_E.
    for factor in [0.7, 1.4]:
        cfg = base_config.model_copy(deep=True)
        cfg.ethylene_kg_h = max(base_config.ethylene_kg_h * factor, 0.1)
        cfg.enb_kg_h = max(base_config.enb_kg_h / factor, 0.1)
        candidates.append(cfg)
    return candidates


def score_candidate_by_uncertainty(candidate: ProcessConfig, parameter_uncertainty: dict[str, float] | None = None) -> tuple[float, str]:
    """Score a candidate by how much it excites weak/uncertain parameters."""
    u = parameter_uncertainty or {}
    score = 0.0
    reasons: list[str] = []
    if u.get("beta_P", 0.0) > 0.5:
        score += abs(candidate.pressure_MPa - 1.0) * 2.0
        reasons.append("pressure gradient for beta_P")
    if u.get("beta_E", 0.0) > 0.5:
        score += candidate.ethylene_kg_h / max(candidate.enb_kg_h, 1.0e-6) * 0.05
        reasons.append("E/ENB gradient for beta_E")
    if u.get("ktr_H2", 0.0) > 0.5:
        score += candidate.hydrogen_g_h / 10.0
        reasons.append("H2 gradient for ktr_H2")
    if u.get("rheology", 0.0) > 0.5:
        score += max(candidate.solvent_mass_kg_h, 1.0) ** -0.2 + abs(candidate.temperature_C - 100.0) / 50.0
        reasons.append("solids/temperature rheology coverage")
    if u.get("Henry", 0.0) > 0.5:
        score += candidate.pressure_MPa
        reasons.append("gas solubility pressure coverage")
    if not reasons:
        score += 1.0
        reasons.append("balanced screening point")
    return float(max(score, 0.0)), "; ".join(reasons)


def score_candidate_by_engineering_feasibility(candidate: ProcessConfig) -> tuple[dict[str, bool], float]:
    """Run light preflight/flowsheet checks and return feasibility flags plus risk."""
    preflight_ok = all(getattr(item, "passed", True) for item in run_preflight_for_flowsheet(candidate))
    try:
        result = run_flowsheet(candidate)
        residual_system = build_flowsheet_residual_system(result)
        residual_ok = residual_system_acceptance(residual_system)["passed"]
        residual_penalty_ok = residual_penalty_for_optimizer(residual_system) < 50.0
        cooling_ok = result.kpis.get("cooling_margin_kW", 0.0) > 0.0
        fouling_ok = result.kpis.get("fouling_index", 0.0) < 3.0
        pressure_ok = result.kpis.get("pipe_pressure_drop_kPa", 0.0) < 250.0
        solids_ok = result.kpis.get("solids_wt", 0.0) < 35.0
    except Exception:
        residual_ok = cooling_ok = fouling_ok = pressure_ok = solids_ok = False
    flags = {"preflight": preflight_ok, "residual_system": residual_ok, "residual_objective": residual_penalty_ok, "cooling_margin": cooling_ok, "fouling": fouling_ok, "pressure_drop": pressure_ok, "solids": solids_ok}
    risk = float(sum(0 if value else 1 for value in flags.values()) / len(flags))
    return flags, risk


def rank_bayesian_doe_candidates(
    template_id: str,
    base_config: ProcessConfig,
    parameter_uncertainty: dict[str, float] | None = None,
    *,
    seed: int = 11,
) -> pd.DataFrame:
    """Rank constrained DOE candidates by uncertainty information and feasibility."""
    rows: list[CandidateExperiment] = []
    rng = np.random.default_rng(seed)
    for cfg in generate_candidate_design_space(template_id, base_config):
        info, rationale = score_candidate_by_uncertainty(cfg, parameter_uncertainty)
        flags, risk = score_candidate_by_engineering_feasibility(cfg)
        if not all(flags.values()):
            continue
        info *= float(0.95 + 0.1 * rng.random())
        rows.append(CandidateExperiment(model_dump_compat(cfg), info, info / (1.0 + risk), risk, flags, rationale))
    df = pd.DataFrame([row.as_dict() for row in rows])
    if df.empty:
        return df
    return df.sort_values(["expected_information_gain", "predicted_risk"], ascending=[False, True]).reset_index(drop=True)


def recommend_next_experiment_batch(
    base_config: ProcessConfig,
    parameter_uncertainty: dict[str, float] | None = None,
    *,
    template_id: str = "EPDM_EPM_metallocene_solution",
    n: int = 6,
    seed: int = 11,
) -> pd.DataFrame:
    """Return the top N feasible uncertainty-driven DOE candidates."""
    return rank_bayesian_doe_candidates(template_id, base_config, parameter_uncertainty, seed=seed).head(n)
