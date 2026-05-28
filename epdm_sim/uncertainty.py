"""Model-confidence and uncertainty analysis for EPDM digital-twin KPIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, run_flowsheet
from .utils import model_dump_compat


@dataclass
class UncertaintyResult:
    """Monte Carlo/LHS uncertainty analysis output."""

    samples: pd.DataFrame
    confidence_intervals: pd.DataFrame
    tornado: pd.DataFrame
    risk_probabilities: dict[str, float]
    model_confidence: dict[str, Any]

    def as_dataframe(self) -> pd.DataFrame:
        """Return confidence intervals as a report table."""
        return self.confidence_intervals.copy()


def run_uncertainty_analysis(
    config: ProcessConfig | dict[str, Any],
    *,
    n_samples: int = 32,
    seed: int = 7,
    method: str = "latin_hypercube",
) -> UncertaintyResult:
    """Run a lightweight uncertainty analysis around the current flowsheet.

    Perturbations cover kinetic intensity, heat of polymerization, Henry/VLE
    volatility proxy and viscosity proxy.  The calculation deliberately reuses
    the fast flowsheet and keeps samples modest for Streamlit responsiveness.
    """
    cfg = config if isinstance(config, ProcessConfig) else ProcessConfig(**config)
    rng = np.random.default_rng(seed)
    n = max(int(n_samples), 4)
    unit = _latin_hypercube(n, 5, rng) if method == "latin_hypercube" else rng.random((n, 5))
    rows: list[dict[str, Any]] = []
    base = model_dump_compat(cfg)
    for i, u in enumerate(unit):
        factors = {
            "kinetic_factor": _scale(u[0], 0.75, 1.25),
            "deltaH_factor": _scale(u[1], 0.90, 1.10),
            "henry_factor": _scale(u[2], 0.85, 1.15),
            "viscosity_factor": _scale(u[3], 0.70, 1.60),
            "flashK_factor": _scale(u[4], 0.85, 1.15),
        }
        payload = dict(base)
        payload["catalyst_umol_h"] = max(float(payload.get("catalyst_umol_h", 100.0)) * factors["kinetic_factor"], 1.0e-9)
        payload["deltaH_ethylene_kJ_mol"] = float(payload.get("deltaH_ethylene_kJ_mol", -95.0)) * factors["deltaH_factor"]
        payload["deltaH_propylene_kJ_mol"] = float(payload.get("deltaH_propylene_kJ_mol", -85.0)) * factors["deltaH_factor"]
        payload["deltaH_ENB_kJ_mol"] = float(payload.get("deltaH_ENB_kJ_mol", -80.0)) * factors["deltaH_factor"]
        payload["solvent_mass_kg_h"] = max(float(payload.get("solvent_mass_kg_h", 100.0)) / max(factors["viscosity_factor"] ** 0.25, 1.0e-6), 1.0e-6)
        payload["flash1_P_MPa"] = max(float(payload.get("flash1_P_MPa", 0.2)) / factors["flashK_factor"], 0.001)
        try:
            sim = run_flowsheet(ProcessConfig(**payload))
            row = {"sample": i, **factors}
            row.update(
                {
                    key: sim.kpis.get(key)
                    for key in [
                        "polymer_kg_h",
                        "C2_wt",
                        "ENB_wt",
                        "Mooney",
                        "Mw",
                        "heat_duty_kW",
                        "cooling_margin_kW",
                        "fouling_index",
                        "pipe_pressure_drop_kPa",
                        "ENB_residue_ppm",
                    ]
                }
            )
        except Exception as exc:
            row = {"sample": i, **factors, "error": str(exc)}
        rows.append(row)
    samples = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    ci = _confidence_intervals(samples)
    tornado = _tornado(samples)
    risk = {
        "probability_cooling_margin_lt_0": _prob(samples.get("cooling_margin_kW"), lambda s: s < 0.0),
        "probability_fouling_index_gt_3": _prob(samples.get("fouling_index"), lambda s: s > 3.0),
        "probability_pressure_drop_gt_100kPa": _prob(samples.get("pipe_pressure_drop_kPa"), lambda s: s > 100.0),
    }
    model_confidence = {
        "sample_count": len(samples),
        "seed": seed,
        "method": method,
        "confidence_level": "研发级趋势置信区间 P05-P95",
        "applicability_score": float(max(0.15, 1.0 - 0.5 * risk["probability_cooling_margin_lt_0"] - 0.3 * risk["probability_fouling_index_gt_3"])),
    }
    return UncertaintyResult(samples, ci, tornado, risk, model_confidence)


def _latin_hypercube(n: int, dims: int, rng: np.random.Generator) -> np.ndarray:
    base = (np.arange(n)[:, None] + rng.random((n, dims))) / n
    for j in range(dims):
        rng.shuffle(base[:, j])
    return base


def _scale(u: float, low: float, high: float) -> float:
    return float(low + (high - low) * u)


def _confidence_intervals(samples: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "polymer_kg_h",
        "C2_wt",
        "ENB_wt",
        "Mooney",
        "Mw",
        "heat_duty_kW",
        "cooling_margin_kW",
        "fouling_index",
        "pipe_pressure_drop_kPa",
        "ENB_residue_ppm",
    ]
    rows = []
    for metric in metrics:
        if metric not in samples:
            continue
        values = pd.to_numeric(samples[metric], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "metric": metric,
                "mean": float(values.mean()),
                "p05": float(values.quantile(0.05)),
                "p50": float(values.quantile(0.50)),
                "p95": float(values.quantile(0.95)),
                "std": float(values.std(ddof=0)),
            }
        )
    return pd.DataFrame(rows)


def _tornado(samples: pd.DataFrame) -> pd.DataFrame:
    factors = ["kinetic_factor", "deltaH_factor", "henry_factor", "viscosity_factor", "flashK_factor"]
    metric = "ENB_wt" if "ENB_wt" in samples else "polymer_kg_h"
    rows = []
    y_raw = samples.get(metric)
    if y_raw is None:
        y = pd.Series([np.nan] * len(samples), index=samples.index)
    else:
        y = pd.to_numeric(y_raw, errors="coerce")
    for factor in factors:
        x = pd.to_numeric(samples.get(factor), errors="coerce")
        mask = x.notna() & y.notna()
        corr = float(np.corrcoef(x[mask], y[mask])[0, 1]) if mask.sum() > 2 else 0.0
        if not np.isfinite(corr):
            corr = 0.0
        rows.append({"factor": factor, "metric": metric, "correlation": corr, "importance": abs(corr)})
    return pd.DataFrame(rows).sort_values("importance", ascending=False)


def _prob(values: pd.Series | None, predicate) -> float:
    if values is None:
        return 0.0
    series = pd.to_numeric(values, errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float(np.mean(predicate(series)))
