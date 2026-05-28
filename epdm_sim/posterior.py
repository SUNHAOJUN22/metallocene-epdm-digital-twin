"""Lightweight posterior sampling for R&D parameter uncertainty."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .kinetics import KineticParameters
from .utils import clamp, positive


PARAMETER_BOUNDS = {
    "k_E_ref": (1.0e5, 1.0e7),
    "k_P_ref": (1.0e5, 1.0e7),
    "k_ENB_ref": (1.0e5, 1.0e7),
    "beta_P": (0.0, 2.0),
    "beta_E": (0.0, 0.2),
    "Mw0": (5.0e4, 2.0e6),
    "ktr_H2": (0.0, 200.0),
    "kd_h": (0.0, 1.0),
}


@dataclass
class PosteriorResult:
    """Result from lightweight MCMC sampling."""

    samples: pd.DataFrame
    parameter_summary: pd.DataFrame
    acceptance_rate: float
    posterior_correlation: pd.DataFrame
    credible_intervals: pd.DataFrame
    warnings: list[str] = field(default_factory=list)

    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "acceptance_rate": self.acceptance_rate,
                    "n_samples": len(self.samples),
                    "warnings": "; ".join(self.warnings),
                }
            ]
        )


def log_prior_bounds(params: dict[str, float], bounds: dict[str, tuple[float, float]] | None = None) -> float:
    """Return a simple uniform log prior inside bounds, -inf outside."""
    bounds = bounds or PARAMETER_BOUNDS
    for key, value in params.items():
        if key in bounds:
            low, high = bounds[key]
            if not np.isfinite(value) or value < low or value > high:
                return -np.inf
    return 0.0


def log_likelihood_proxy(params: dict[str, float], dataset: pd.DataFrame | None = None, target_metrics: list[str] | None = None) -> float:
    """Return a stable proxy likelihood against endpoint experiment data."""
    p = KineticParameters(**{**KineticParameters().model_dump(), **params} if hasattr(KineticParameters(), "model_dump") else params)
    if dataset is None or dataset.empty:
        # Weak prior around default parameters keeps sampling finite.
        defaults = KineticParameters()
        return -0.5 * (
            ((np.log(p.k_E_ref) - np.log(defaults.k_E_ref)) / 1.0) ** 2
            + ((np.log(p.k_P_ref) - np.log(defaults.k_P_ref)) / 1.0) ** 2
            + ((p.beta_P - defaults.beta_P) / 0.5) ** 2
            + ((p.ktr_H2 - defaults.ktr_H2) / 50.0) ** 2
        )
    targets = target_metrics or ["C2_wt", "ENB_wt", "Mw", "Mooney"]
    score = 0.0
    for _, row in dataset.iterrows():
        pred_c2 = 50.0 + 20.0 * (p.k_E_ref / max(p.k_E_ref + p.k_P_ref, 1.0))
        pred_enb = max(0.0, min(12.0, 2.0 + 2.0e-6 * p.k_ENB_ref / (1.0 + p.beta_P)))
        pred_mw = p.Mw0 / (1.0 + 0.01 * p.ktr_H2)
        pred_mooney = max(5.0, pred_mw / 6500.0)
        residuals = {
            "C2_wt": (pred_c2 - float(row.get("C2_wt", pred_c2))) / 8.0,
            "ENB_wt": (pred_enb - float(row.get("ENB_wt", pred_enb))) / 3.0,
            "Mw": (pred_mw - float(row.get("Mw", pred_mw))) / 150000.0,
            "Mooney": (pred_mooney - float(row.get("Mooney", pred_mooney))) / 35.0,
        }
        score -= 0.5 * sum(residuals[key] ** 2 for key in targets if key in residuals)
    return float(score)


def posterior_summary(samples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return summary, credible intervals and correlation tables."""
    if samples.empty:
        empty = pd.DataFrame()
        return empty, empty, empty
    summary_rows = []
    ci_rows = []
    for col in samples.columns:
        values = samples[col].to_numpy(dtype=float)
        summary_rows.append({"parameter": col, "mean": float(np.mean(values)), "std": float(np.std(values)), "median": float(np.median(values))})
        ci_rows.append({"parameter": col, "p05": float(np.percentile(values, 5)), "p50": float(np.percentile(values, 50)), "p95": float(np.percentile(values, 95))})
    corr = samples.corr(numeric_only=True).fillna(0.0)
    return pd.DataFrame(summary_rows), pd.DataFrame(ci_rows), corr


def run_lightweight_mcmc(
    dataset: pd.DataFrame | None = None,
    parameter_set: dict[str, float] | None = None,
    target_metrics: list[str] | None = None,
    n_steps: int = 120,
    seed: int = 7,
) -> PosteriorResult:
    """Run a bounded random-walk Metropolis sampler."""
    rng = np.random.default_rng(seed)
    base = KineticParameters()
    current = {
        key: float((parameter_set or {}).get(key, getattr(base, key)))
        for key in PARAMETER_BOUNDS
    }
    current_lp = log_prior_bounds(current) + log_likelihood_proxy(current, dataset, target_metrics)
    rows: list[dict[str, float]] = []
    accepted = 0
    warnings: list[str] = []
    n_steps = max(int(n_steps), 10)
    for _ in range(n_steps):
        proposal = dict(current)
        for key, (low, high) in PARAMETER_BOUNDS.items():
            scale = 0.08 * (high - low)
            if key.startswith("k_") or key == "Mw0":
                proposal[key] = float(np.exp(np.log(max(current[key], 1.0)) + rng.normal(0.0, 0.08)))
            else:
                proposal[key] = float(current[key] + rng.normal(0.0, scale))
            proposal[key] = clamp(proposal[key], low, high)
        prior = log_prior_bounds(proposal)
        proposal_lp = prior + log_likelihood_proxy(proposal, dataset, target_metrics) if np.isfinite(prior) else -np.inf
        if np.log(rng.uniform()) < proposal_lp - current_lp:
            current = proposal
            current_lp = proposal_lp
            accepted += 1
        rows.append(dict(current))
    samples = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).dropna()
    if samples.empty:
        warnings.append("Posterior sampler produced no finite samples; using default parameter row.")
        samples = pd.DataFrame([current])
    summary, ci, corr = posterior_summary(samples)
    return PosteriorResult(samples, summary, accepted / n_steps, corr, ci, warnings)


def posterior_to_uncertainty_inputs(result: PosteriorResult) -> dict[str, float]:
    """Convert posterior intervals to uncertainty percentages."""
    output = {}
    for _, row in result.credible_intervals.iterrows():
        median = positive(float(row["p50"]), 1.0)
        output[str(row["parameter"])] = 100.0 * abs(float(row["p95"]) - float(row["p05"])) / max(2.0 * median, 1.0e-12)
    return output

