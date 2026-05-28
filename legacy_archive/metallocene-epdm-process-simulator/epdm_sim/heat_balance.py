"""Reaction heat, cooling duty and heat-transfer calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from pydantic import BaseModel

from .utils import TINY, clamp, positive, safe_divide


class HeatBalanceConfig(BaseModel):
    """Heat-balance inputs with engineering-estimate defaults."""

    deltaH_polymerization: dict[str, float] = {
        "ethylene": -95.0,
        "propylene": -85.0,
        "ENB": -80.0,
    }
    overall_U_W_m2K: float = 300.0
    heat_transfer_area_m2: float = 2.0
    coolant_inlet_C: float = 25.0
    coolant_outlet_C: float = 35.0
    reactor_temperature_C: float = 100.0


@dataclass
class HeatBalanceResult:
    """Calculated heat balance and heat-removal indicators."""

    Q_rxn_kJ_h: float
    Q_rxn_kW: float
    preheat_kJ_h: float
    preheat_kW: float
    devol_kJ_h: float
    devol_kW: float
    sensible_heat_kW: float
    Q_cooling_kW: float
    total_utility_kW: float
    mass_holdup_kg: float
    Cp_mix_kJ_kgK: float
    deltaT_ad_K: float
    thermal_risk: str
    Q_max_kW: float
    cooling_margin_kW: float
    lmtd_K: float
    heat_transfer_status: str
    deltaH_polymerization: dict[str, float]

    def as_dataframe(self) -> pd.DataFrame:
        """Return the heat-balance result as a report table."""
        rows = [
            ("聚合反应热", self.Q_rxn_kW, "kW"),
            ("预热负荷", self.preheat_kW, "kW"),
            ("脱挥负荷", self.devol_kW, "kW"),
            ("所需冷却负荷", self.Q_cooling_kW, "kW"),
            ("总公用工程负荷", self.total_utility_kW, "kW"),
            ("绝热温升", self.deltaT_ad_K, "K"),
            ("热风险等级", self.thermal_risk, "-"),
            ("最大可移热能力", self.Q_max_kW, "kW"),
            ("移热裕度", self.cooling_margin_kW, "kW"),
            ("夹套LMTD", self.lmtd_K, "K"),
        ]
        return pd.DataFrame(rows, columns=["item", "value", "unit"])


def calculate_reaction_heat(
    mol_consumed_h: dict[str, float],
    deltaH_polymerization: dict[str, float] | None = None,
) -> float:
    """Return positive polymerization heat release in kJ/h.

    deltaH values are negative by convention. The returned value is positive
    and represents heat that must be removed.
    """
    delta_h = deltaH_polymerization or HeatBalanceConfig().deltaH_polymerization
    heat_sum = 0.0
    for monomer in ("ethylene", "propylene", "ENB"):
        heat_sum += positive(mol_consumed_h.get(monomer, 0.0)) * float(delta_h.get(monomer, 0.0))
    return max(-heat_sum, 0.0)


def thermal_risk_level(deltaT_ad_K: float) -> str:
    """Classify adiabatic temperature-rise risk."""
    if deltaT_ad_K < 5.0:
        return "low"
    if deltaT_ad_K <= 20.0:
        return "medium"
    return "high"


def calculate_lmtd(reactor_temperature_C: float, coolant_inlet_C: float, coolant_outlet_C: float) -> float:
    """Calculate jacket/cooler log-mean temperature difference in K."""
    dt_hot_end = reactor_temperature_C - coolant_outlet_C
    dt_cold_end = reactor_temperature_C - coolant_inlet_C
    dt1 = max(dt_hot_end, TINY)
    dt2 = max(dt_cold_end, TINY)
    if abs(dt1 - dt2) < 1.0e-9:
        return dt1
    return safe_divide(dt2 - dt1, math.log(dt2 / dt1), min(dt1, dt2))


def heat_transfer_capacity_kW(
    overall_U_W_m2K: float,
    heat_transfer_area_m2: float,
    reactor_temperature_C: float,
    coolant_inlet_C: float,
    coolant_outlet_C: float,
) -> tuple[float, float]:
    """Return maximum removable heat in kW and the LMTD in K."""
    lmtd = calculate_lmtd(reactor_temperature_C, coolant_inlet_C, coolant_outlet_C)
    q_max = positive(overall_U_W_m2K) * positive(heat_transfer_area_m2) * lmtd / 1000.0
    return q_max, lmtd


def calculate_heat_balance(
    mol_consumed_h: dict[str, float],
    mass_holdup_kg: float,
    Cp_mix_kJ_kgK: float,
    preheat_kJ_h: float = 0.0,
    devol_kJ_h: float = 0.0,
    sensible_heat_kJ_h: float = 0.0,
    config: HeatBalanceConfig | None = None,
) -> HeatBalanceResult:
    """Calculate reaction heat, adiabatic rise, cooling load and heat-transfer margin."""
    cfg = config or HeatBalanceConfig()
    q_rxn_kJ_h = calculate_reaction_heat(mol_consumed_h, cfg.deltaH_polymerization)
    q_rxn_kW = q_rxn_kJ_h / 3600.0
    preheat_kW = preheat_kJ_h / 3600.0
    devol_kW = devol_kJ_h / 3600.0
    sensible_heat_kW = max(sensible_heat_kJ_h, 0.0) / 3600.0
    q_cooling_kW = q_rxn_kW + sensible_heat_kW
    total_utility_kW = abs(preheat_kW) + q_cooling_kW + abs(devol_kW)
    deltaT_ad = safe_divide(q_rxn_kJ_h, max(positive(mass_holdup_kg) * positive(Cp_mix_kJ_kgK), TINY), 0.0)
    q_max_kW, lmtd = heat_transfer_capacity_kW(
        cfg.overall_U_W_m2K,
        cfg.heat_transfer_area_m2,
        cfg.reactor_temperature_C,
        cfg.coolant_inlet_C,
        cfg.coolant_outlet_C,
    )
    margin = q_max_kW - q_rxn_kW
    status = "移热能力充足" if margin >= 0.0 else "移热能力不足，存在温升和失控风险"
    return HeatBalanceResult(
        Q_rxn_kJ_h=q_rxn_kJ_h,
        Q_rxn_kW=q_rxn_kW,
        preheat_kJ_h=preheat_kJ_h,
        preheat_kW=preheat_kW,
        devol_kJ_h=devol_kJ_h,
        devol_kW=devol_kW,
        sensible_heat_kW=sensible_heat_kW,
        Q_cooling_kW=q_cooling_kW,
        total_utility_kW=total_utility_kW,
        mass_holdup_kg=positive(mass_holdup_kg),
        Cp_mix_kJ_kgK=positive(Cp_mix_kJ_kgK),
        deltaT_ad_K=deltaT_ad,
        thermal_risk=thermal_risk_level(deltaT_ad),
        Q_max_kW=q_max_kW,
        cooling_margin_kW=margin,
        lmtd_K=lmtd,
        heat_transfer_status=status,
        deltaH_polymerization=dict(cfg.deltaH_polymerization),
    )
