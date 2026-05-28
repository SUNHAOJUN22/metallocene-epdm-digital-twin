"""Feasible DOE recommendation helpers for parameter information gain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .flowsheet import ProcessConfig, load_default_config, run_flowsheet


@dataclass
class DOEOptimalResult:
    """Recommended next experiments."""

    recommendations: pd.DataFrame
    rejected: pd.DataFrame

    def as_dataframe(self) -> pd.DataFrame:
        return self.recommendations.copy()


def _with(cfg: ProcessConfig, **updates: Any) -> ProcessConfig:
    new = cfg.model_copy(deep=True)
    for key, value in updates.items():
        setattr(new, key, value)
    return new


def recommend_optimal_doe(base_config: ProcessConfig | None = None, max_experiments: int = 8) -> DOEOptimalResult:
    """Return feasible DOE points covering kinetics, transfer and rheology parameters."""
    base = base_config or load_default_config()
    candidates = [
        ("pressure_low_enb", {"pressure_MPa": 0.7, "enb_kg_h": max(base.enb_kg_h * 1.8, 5.0)}, "辨识beta_P和ENB引入窗口"),
        ("pressure_high_enb", {"pressure_MPa": 2.0, "enb_kg_h": max(base.enb_kg_h * 1.8, 5.0)}, "验证高压ENB抑制项"),
        ("h2_low", {"hydrogen_g_h": max(base.hydrogen_g_h * 0.1, 0.1)}, "辨识无/低氢Mw上限"),
        ("h2_high", {"hydrogen_g_h": max(base.hydrogen_g_h * 8.0, 20.0)}, "辨识ktr_H2与门尼响应"),
        ("temperature_low", {"temperature_C": max(base.temperature_C - 15.0, 70.0)}, "辨识Arrhenius温度响应"),
        ("temperature_high", {"temperature_C": min(base.temperature_C + 20.0, 140.0)}, "辨识活性与热负荷"),
        ("alti_low", {"AlTi_ratio": 250.0}, "辨识MAO活化窗口"),
        ("bht_screen", {"BHT_ratio": 0.5, "AlTi_ratio": 500.0}, "验证BHT降低MAO用量规律"),
        ("ethylene_rich", {"ethylene_kg_h": base.ethylene_kg_h * 1.4, "propylene_kg_h": max(base.propylene_kg_h * 0.75, 1.0)}, "辨识beta_E乙烯竞争插入"),
        ("rpm_high", {"agitation_rpm": base.agitation_rpm * 1.4}, "辨识kLa/混合与挂胶风险"),
    ]
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for run_id, updates, why in candidates:
        cfg = _with(base, **updates)
        try:
            result = run_flowsheet(cfg)
            feasible = result.kpis["cooling_margin_kW"] > 0.0 and result.kpis["fouling_index"] < 3.0
            row = {
                "candidate_id": run_id,
                "why": why,
                "temperature_C": cfg.temperature_C,
                "pressure_MPa": cfg.pressure_MPa,
                "ethylene_kg_h": cfg.ethylene_kg_h,
                "propylene_kg_h": cfg.propylene_kg_h,
                "enb_kg_h": cfg.enb_kg_h,
                "hydrogen_g_h": cfg.hydrogen_g_h,
                "AlTi_ratio": cfg.AlTi_ratio,
                "BHT_ratio": cfg.BHT_ratio,
                "rpm": cfg.agitation_rpm,
                "cooling_margin_kW": result.kpis["cooling_margin_kW"],
                "fouling_index": result.kpis["fouling_index"],
                "ENB_wt": result.kpis["ENB_wt"],
                "Mw": result.kpis["Mw"],
            }
            (rows if feasible else rejected).append(row)
        except Exception as exc:
            rejected.append({"candidate_id": run_id, "why": why, "error": str(exc)})
    return DOEOptimalResult(pd.DataFrame(rows).head(max_experiments), pd.DataFrame(rejected))
