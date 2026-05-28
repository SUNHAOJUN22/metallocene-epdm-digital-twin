"""Multi-objective process-window scan and Pareto frontier selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, run_flowsheet
from .polymer_props import grade_match
from .utils import model_dump_compat


@dataclass
class ParetoResult:
    """Pareto scan result."""

    candidates: pd.DataFrame
    frontier: pd.DataFrame
    recommended_windows: pd.DataFrame

    @property
    def recommended(self) -> pd.DataFrame:
        """Backward-compatible alias for recommended windows."""
        return self.recommended_windows


def generate_pareto_windows(
    base: ProcessConfig,
    grade_id: str = "Internal_1109_2_commercial_candidate",
    *,
    n_samples: int = 36,
    seed: int = 11,
    pressure_drop_limit_kPa: float = 500.0,
    enb_residue_threshold_ppm: float = 100000.0,
    max_solids_wt: float = 30.0,
) -> ParetoResult:
    """Generate feasible candidates and a simple nondominated frontier."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for idx in range(max(n_samples, 6)):
        cfg = ProcessConfig(**model_dump_compat(base))
        cfg.temperature_C = float(rng.uniform(85.0, 130.0))
        cfg.pressure_MPa = float(rng.uniform(0.55, 1.8))
        ep_ratio = float(rng.uniform(0.45, 2.8))
        total_ep = max(base.ethylene_kg_h + base.propylene_kg_h, 1.0)
        cfg.ethylene_kg_h = total_ep * ep_ratio / (1.0 + ep_ratio)
        cfg.propylene_kg_h = total_ep / (1.0 + ep_ratio)
        cfg.enb_kg_h = float(rng.uniform(max(base.enb_kg_h * 0.3, 0.1), max(base.enb_kg_h * 2.8, 6.0)))
        cfg.hydrogen_g_h = float(rng.uniform(0.0, max(base.hydrogen_g_h * 4.0, 20.0)))
        cfg.residence_time_min = float(rng.uniform(12.0, 90.0))
        cfg.heat_transfer_area_m2 = float(rng.uniform(max(base.heat_transfer_area_m2 * 0.7, 0.2), max(base.heat_transfer_area_m2 * 2.5, 3.0)))
        result = run_flowsheet(cfg)
        k = result.kpis
        match = grade_match(k, grade_id)
        feasible = (
            k["cooling_margin_kW"] > 0
            and k["fouling_index"] < 3.0
            and k["pipe_pressure_drop_kPa"] <= pressure_drop_limit_kPa
            and k["solids_wt"] <= max_solids_wt
            and k["ENB_residue_ppm"] <= enb_residue_threshold_ppm
        )
        rows.append(
            {
                "candidate": idx,
                "feasible": feasible,
                "grade_score": match["score"],
                "ENB_wt": k["ENB_wt"],
                "ENB_residue_ppm": k["ENB_residue_ppm"],
                "fouling_index": k["fouling_index"],
                "heat_duty_kW": k["heat_duty_kW"],
                "cooling_margin_kW": k["cooling_margin_kW"],
                "pressure_drop_kPa": k["pipe_pressure_drop_kPa"],
                "pipe_pressure_drop_kPa": k["pipe_pressure_drop_kPa"],
                "solids_wt": k["solids_wt"],
                "temperature_C": cfg.temperature_C,
                "pressure_MPa": cfg.pressure_MPa,
                "ethylene_kg_h": cfg.ethylene_kg_h,
                "propylene_kg_h": cfg.propylene_kg_h,
                "enb_kg_h": cfg.enb_kg_h,
                "hydrogen_g_h": cfg.hydrogen_g_h,
                "residence_time_min": cfg.residence_time_min,
                "heat_transfer_area_m2": cfg.heat_transfer_area_m2,
            }
        )
    candidates = pd.DataFrame(rows)
    feasible_df = candidates[candidates["feasible"]].copy()
    if feasible_df.empty:
        feasible_df = candidates.copy()
    frontier = _nondominated(feasible_df)
    recommended = _recommended_windows(frontier)
    return ParetoResult(candidates=candidates, frontier=frontier, recommended_windows=recommended)


def _nondominated(df: pd.DataFrame) -> pd.DataFrame:
    """Return nondominated rows for mixed maximize/minimize objectives."""
    values = df[["grade_score", "ENB_wt", "cooling_margin_kW", "ENB_residue_ppm", "fouling_index", "heat_duty_kW", "pressure_drop_kPa"]].to_numpy(float)
    maximize = np.array([1, 1, 1, -1, -1, -1, -1], dtype=float)
    scores = values * maximize
    keep = []
    for i in range(len(df)):
        dominated = False
        for j in range(len(df)):
            if i == j:
                continue
            if np.all(scores[j] >= scores[i]) and np.any(scores[j] > scores[i]):
                dominated = True
                break
        keep.append(not dominated)
    return df.loc[keep].sort_values(["grade_score", "ENB_wt"], ascending=False).reset_index(drop=True)


def _recommended_windows(frontier: pd.DataFrame) -> pd.DataFrame:
    """Select robust, high-ENB and low-risk windows."""
    if frontier.empty:
        return pd.DataFrame()
    picks = []
    robust_idx = (frontier["grade_score"] + 2.0 * frontier["cooling_margin_kW"] - 10.0 * frontier["fouling_index"]).idxmax()
    high_enb_idx = frontier["ENB_wt"].idxmax()
    low_risk_idx = (frontier["fouling_index"] + frontier["pressure_drop_kPa"] / 100.0 - frontier["cooling_margin_kW"]).idxmin()
    for label, idx in [("稳健窗口", robust_idx), ("高ENB窗口", high_enb_idx), ("低风险窗口", low_risk_idx)]:
        row = frontier.loc[idx].to_dict()
        row["window"] = label
        picks.append(row)
    return pd.DataFrame(picks)
