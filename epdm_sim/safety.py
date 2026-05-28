"""Thermal safety screening for R&D EPDM polymerization cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .utils import safe_divide


@dataclass
class SafetyResult:
    """Thermal safety and runaway screening result."""

    heat_accumulation_kW: float
    cooling_failure_deltaT_K: float
    time_to_high_temp_alarm_min: float
    MTSR_like_C: float
    cooling_margin_class: str
    runaway_risk_level: str
    recommendations: list[str]

    def as_dataframe(self) -> pd.DataFrame:
        """Return a one-row safety table."""
        return pd.DataFrame(
            [
                {
                    "heat_accumulation_kW": self.heat_accumulation_kW,
                    "cooling_failure_deltaT_K": self.cooling_failure_deltaT_K,
                    "time_to_high_temp_alarm_min": self.time_to_high_temp_alarm_min,
                    "MTSR_like_C": self.MTSR_like_C,
                    "cooling_margin_class": self.cooling_margin_class,
                    "runaway_risk_level": self.runaway_risk_level,
                    "recommendations": "；".join(self.recommendations),
                }
            ]
        )


def calculate_safety(
    result: Any,
    dynamic_profile: pd.DataFrame | None = None,
    *,
    high_temp_alarm_C: float = 130.0,
) -> SafetyResult:
    """Calculate a compact heat-safety screen from flowsheet and optional time-series data."""
    k = result.kpis
    heat_kW = float(k.get("heat_duty_kW", 0.0))
    q_max = float(k.get("Q_max_kW", 0.0))
    margin = float(k.get("cooling_margin_kW", q_max - heat_kW))
    cp = max(float(k.get("Cp_liq_kJ_kgK", 2.0)), 0.1)
    rho = max(float(k.get("liquid_density_kg_m3", 650.0)), 1.0)
    volume_m3 = max(float(result.config.reactor_volume_L) / 1000.0, 1.0e-6)
    holdup_kg = rho * volume_m3
    accumulation = max(heat_kW - q_max, 0.0)
    failure_delta_t = safe_divide(heat_kW * 60.0, holdup_kg * cp, 0.0)
    base_T = float(result.config.temperature_C)
    if dynamic_profile is not None and not dynamic_profile.empty and "T_C" in dynamic_profile:
        base_T = float(dynamic_profile["T_C"].max())
        max_heat = float(dynamic_profile.get("Q_rxn_kW", pd.Series([heat_kW])).max())
        heat_kW = max(heat_kW, max_heat)
    MTSR_like = base_T + float(k.get("deltaT_ad_K", failure_delta_t))
    if margin >= 0.2 * max(heat_kW, 1.0e-9):
        margin_class = "adequate"
    elif margin >= 0.0:
        margin_class = "tight"
    else:
        margin_class = "insufficient"
    time_to_alarm = safe_divide((high_temp_alarm_C - base_T) * holdup_kg * cp, max(accumulation, 1.0e-9) * 60.0, float("inf"))
    if margin_class == "insufficient" or MTSR_like > high_temp_alarm_C + 20.0:
        risk = "high"
    elif margin_class == "tight" or MTSR_like > high_temp_alarm_C:
        risk = "medium"
    else:
        risk = "low"
    recs: list[str] = []
    if margin_class != "adequate":
        recs.append("增加夹套/内盘管换热面积或提高冷却介质流量。")
    if failure_delta_t > 20.0:
        recs.append("降低催化剂浓度或采用分段催化剂/ENB进料以削峰。")
    if float(k.get("solids_wt", 0.0)) > 18.0:
        recs.append("降低目标固含或提高溶剂比，避免黏度升高导致U下降。")
    if float(k.get("fouling_index", 0.0)) > 3.0:
        recs.append("提高壁面剪切、降低Mw或使用适合高黏体系的搅拌桨。")
    if not recs:
        recs.append("当前热安全筛查未显示明显冷却不足，仍需用反应量热和中试验证。")
    return SafetyResult(
        heat_accumulation_kW=accumulation,
        cooling_failure_deltaT_K=failure_delta_t,
        time_to_high_temp_alarm_min=time_to_alarm,
        MTSR_like_C=MTSR_like,
        cooling_margin_class=margin_class,
        runaway_risk_level=risk,
        recommendations=recs,
    )
