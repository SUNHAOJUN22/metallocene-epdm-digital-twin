"""Dynamic stirred-tank and semi-batch reactor model for EPDM solution polymerization."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from .components import load_components
from .flowsheet import ProcessConfig
from .kinetics import KineticParameters, active_center_concentration, reaction_rates
from .polymer_props import estimate_mooney
from .solubility import liquid_saturation_concentration_mol_L
from .utils import R_GAS, TINY, c_to_k, clamp, positive, safe_divide


class DynamicReactorConfig(BaseModel):
    """Configuration for realistic batch/semi-batch stirred-tank simulation."""

    mode: str = "Semi-batch Reactor"
    total_time_min: float = 60.0
    dt_min: float = 1.0
    rpm: float = 500.0
    impeller_diameter_m: float = 0.08
    impeller_type: str = "Rushton turbine"
    baffles_enabled: bool = True
    gas_feed_mode: str = "恒压补料"
    enb_feed_strategy: str = "一次加入"
    catalyst_feed_strategy: str = "一次注入"
    hydrogen_feed_strategy: str = "初始加入"
    coolant_C: float = 35.0
    liquid_fill_fraction: float = 0.75
    grade_transition_target: str = "Internal_high_ENB_candidate"


@dataclass
class DynamicReactorResult:
    """Time-profile output from the dynamic reactor model."""

    config: DynamicReactorConfig
    profile: pd.DataFrame
    stages: pd.DataFrame
    summary: dict[str, Any]

    def time_profile(self) -> pd.DataFrame:
        """Return the dynamic time profile."""
        return self.profile.copy()


STAGES = [
    ("充氮/惰化", 0.00, 0.04),
    ("加入溶剂", 0.04, 0.10),
    ("加入ENB", 0.10, 0.16),
    ("升温", 0.16, 0.25),
    ("乙烯/丙烯/H2充压", 0.25, 0.32),
    ("注入催化剂/MAO/BHT", 0.32, 0.36),
    ("聚合反应", 0.36, 0.72),
    ("恒压补料", 0.40, 0.82),
    ("温度控制", 0.36, 0.88),
    ("终止反应", 0.88, 0.92),
    ("出料", 0.92, 0.95),
    ("闪蒸脱单体", 0.95, 0.97),
    ("脱挥脱溶剂", 0.97, 0.99),
    ("产品收集", 0.99, 1.00),
]


def stage_timeline(total_time_min: float) -> pd.DataFrame:
    """Return a standard batch-polymerization operating timeline."""
    rows = []
    for name, start, end in STAGES:
        rows.append(
            {
                "stage": name,
                "start_min": start * total_time_min,
                "end_min": end * total_time_min,
                "duration_min": max((end - start) * total_time_min, 0.0),
            }
        )
    return pd.DataFrame(rows)


def simulate_dynamic_reactor(process: ProcessConfig, dyn: DynamicReactorConfig | None = None) -> DynamicReactorResult:
    """Simulate a realistic stirred-tank, semi-batch, or transition polymerization cycle."""
    cfg = dyn or DynamicReactorConfig(total_time_min=max(process.residence_time_min, 45.0))
    comps = load_components()
    kin = KineticParameters(
        dH_E_kJ_mol=process.deltaH_ethylene_kJ_mol,
        dH_P_kJ_mol=process.deltaH_propylene_kJ_mol,
        dH_ENB_kJ_mol=process.deltaH_ENB_kJ_mol,
    )
    total_time_h = max(cfg.total_time_min / 60.0, 1.0e-6)
    dt_h = max(cfg.dt_min / 60.0, 1.0e-4)
    n_steps = int(math.ceil(total_time_h / dt_h)) + 1
    liquid_volume_L = max(process.reactor_volume_L * cfg.liquid_fill_fraction, 0.05)
    liquid_volume_m3 = liquid_volume_L / 1000.0

    solvent_mass_kg = max(process.solvent_mass_kg_h * total_time_h, 0.05)
    initial_enb_fraction = 1.0 if cfg.enb_feed_strategy == "一次加入" else 0.25
    N_enb = process.enb_kg_h * total_time_h * initial_enb_fraction / (comps["ENB"].MW / 1000.0)
    N_E = 0.06 * process.ethylene_kg_h * total_time_h / (comps["ethylene"].MW / 1000.0)
    N_P = 0.06 * process.propylene_kg_h * total_time_h / (comps["propylene"].MW / 1000.0)
    N_H2 = 0.02 * process.hydrogen_g_h / 1000.0 * total_time_h / (comps["hydrogen"].MW / 1000.0)
    polymer_kg = 0.0
    T_C = process.temperature_C - 8.0

    rows: list[dict[str, Any]] = []
    for step in range(n_steps):
        t_h = min(step * dt_h, total_time_h)
        t_min = t_h * 60.0
        progress = safe_divide(t_h, total_time_h, 0.0)
        active = 1.0 if 0.32 <= progress <= 0.90 else 0.0
        mode_factor = _mode_factor(cfg.mode, progress)
        feed_factor = _feed_factor(cfg.mode, cfg.gas_feed_mode, progress)
        transition_factor = _transition_factor(cfg.mode, progress)

        total_mass_kg = solvent_mass_kg + polymer_kg + _monomer_mass(N_E, N_P, N_enb, N_H2, comps)
        solids_wt = 100.0 * polymer_kg / max(total_mass_kg, TINY)
        mu = _solution_viscosity(T_C, solids_wt, _estimate_mw(N_H2, liquid_volume_L, kin.Mw0, T_C, progress))
        kLa_E = _kla(cfg, mu, "ethylene")
        kLa_P = _kla(cfg, mu, "propylene")
        kLa_H2 = _kla(cfg, mu, "hydrogen")

        y_E, y_P, y_H2 = _gas_mole_fractions(process, transition_factor)
        Cstar_E = _solubility_star("ethylene", y_E, process.pressure_MPa, T_C)
        Cstar_P = _solubility_star("propylene", y_P, process.pressure_MPa, T_C)
        Cstar_H2 = _solubility_star("hydrogen", y_H2, process.pressure_MPa, T_C)
        C_E = N_E / liquid_volume_L
        C_P = N_P / liquid_volume_L
        C_ENB = N_enb / liquid_volume_L
        C_H2 = N_H2 / liquid_volume_L

        feed_E = feed_factor * process.ethylene_kg_h / (comps["ethylene"].MW / 1000.0)
        feed_P = feed_factor * process.propylene_kg_h / (comps["propylene"].MW / 1000.0)
        feed_H2 = (feed_factor if cfg.hydrogen_feed_strategy == "连续补入" else 0.0) * process.hydrogen_g_h / 1000.0 / (comps["hydrogen"].MW / 1000.0)
        feed_ENB = _enb_feed_mol_h(process, cfg, progress, total_time_h, comps)

        transfer_E = kLa_E * max(Cstar_E - C_E, -0.5 * C_E) * liquid_volume_L
        transfer_P = kLa_P * max(Cstar_P - C_P, -0.5 * C_P) * liquid_volume_L
        transfer_H2 = kLa_H2 * max(Cstar_H2 - C_H2, -0.5 * C_H2) * liquid_volume_L

        Cstar_cat = active_center_concentration(
            process.catalyst_umol_h * active * mode_factor,
            liquid_volume_L,
            process.AlTi_ratio,
            process.BHT_ratio,
            t_h,
            kin,
        )
        rates = reaction_rates({"ethylene": C_E, "propylene": C_P, "ENB": C_ENB}, Cstar_cat, c_to_k(T_C), process.pressure_MPa, kin)
        r_E = min(rates.r_E_mol_L_h * liquid_volume_L, max((N_E + max(transfer_E, 0.0) * dt_h) / dt_h, 0.0))
        r_P = min(rates.r_P_mol_L_h * liquid_volume_L, max((N_P + max(transfer_P, 0.0) * dt_h) / dt_h, 0.0))
        r_ENB = min(rates.r_ENB_mol_L_h * liquid_volume_L, max((N_enb + max(feed_ENB, 0.0) * dt_h) / dt_h, 0.0))

        if step > 0:
            N_E = max(N_E + (feed_E + transfer_E - r_E) * dt_h, 0.0)
            N_P = max(N_P + (feed_P + transfer_P - r_P) * dt_h, 0.0)
            N_H2 = max(N_H2 + (feed_H2 + transfer_H2 - 0.005 * r_E) * dt_h, 0.0)
            N_enb = max(N_enb + (feed_ENB - r_ENB) * dt_h, 0.0)
            polymer_kg += (
                r_E * comps["ethylene"].MW
                + r_P * comps["propylene"].MW
                + r_ENB * comps["ENB"].MW
            ) / 1000.0 * dt_h
            Q_rxn_kJ_h = -(r_E * kin.dH_E_kJ_mol + r_P * kin.dH_P_kJ_mol + r_ENB * kin.dH_ENB_kJ_mol)
            mixing = mixing_power(process, cfg, mu)
            U_eff = _effective_U(process.heat_transfer_U_W_m2K, mu, solids_wt)
            Q_removed_kJ_h = max(U_eff * process.heat_transfer_area_m2 * (T_C - cfg.coolant_C), 0.0) * 3.6
            Q_feed_kJ_h = (feed_E + feed_P) * 0.6 * (process.temperature_C - T_C)
            heat_capacity_kJ_K = max(total_mass_kg * 2.1, 1.0)
            T_C += (Q_rxn_kJ_h - Q_removed_kJ_h + Q_feed_kJ_h + mixing["mixing_power_kW"] * 3600.0) * dt_h / heat_capacity_kJ_K
            T_C = clamp(T_C, cfg.coolant_C, process.temperature_C + 80.0)

        C2_mass = polymer_kg * _instant_composition(r_E, r_P, r_ENB, comps)["C2_wt"] / 100.0 if polymer_kg > 0 else 0.0
        comp = _instant_composition(r_E, r_P, r_ENB, comps)
        Mw = _estimate_mw(N_H2, liquid_volume_L, kin.Mw0, T_C, progress)
        PDI = clamp(2.55 + 0.25 * progress + 0.35 * safe_divide(solids_wt, 30.0, 0.0), 2.1, 5.5)
        mooney = estimate_mooney(Mw, PDI, comp["C2_wt"], comp["ENB_wt"])
        mixing = mixing_power(process, cfg, mu)
        rows.append(
            {
                "time_min": t_min,
                "stage": _stage_name(progress),
                "T_C": T_C,
                "P_MPa": process.pressure_MPa,
                "C_E_mol_L": N_E / liquid_volume_L,
                "C_P_mol_L": N_P / liquid_volume_L,
                "C_ENB_mol_L": N_enb / liquid_volume_L,
                "C_H2_mol_L": N_H2 / liquid_volume_L,
                "conversion_pct": 100.0 * polymer_kg / max(polymer_kg + _monomer_mass(N_E, N_P, N_enb, 0.0, comps), TINY),
                "Q_rxn_kW": max(-(r_E * kin.dH_E_kJ_mol + r_P * kin.dH_P_kJ_mol + r_ENB * kin.dH_ENB_kJ_mol) / 3600.0, 0.0),
                "solids_wt": solids_wt,
                "viscosity_Pa_s": mu,
                "Mw": Mw,
                "PDI": PDI,
                "Mooney": mooney,
                "C2_wt": comp["C2_wt"],
                "C3_wt": comp["C3_wt"],
                "ENB_wt": comp["ENB_wt"],
                "r_E_mol_h": r_E,
                "r_P_mol_h": r_P,
                "r_ENB_mol_h": r_ENB,
                "kLa_E_h": kLa_E,
                "kLa_P_h": kLa_P,
                "U_eff_W_m2K": _effective_U(process.heat_transfer_U_W_m2K, mu, solids_wt),
                "mixing_power_kW": mixing["mixing_power_kW"],
                "power_per_volume_kW_m3": mixing["power_per_volume_kW_m3"],
                "impeller_Re": mixing["impeller_Re"],
                "mixing_regime": mixing["mixing_regime"],
                "fouling_index": _fouling_index(solids_wt, mu, T_C),
            }
        )

    profile = pd.DataFrame(rows)
    last = profile.iloc[-1].to_dict()
    summary = {
        "final_conversion_pct": last["conversion_pct"],
        "final_solids_wt": last["solids_wt"],
        "final_viscosity_Pa_s": last["viscosity_Pa_s"],
        "final_Mw": last["Mw"],
        "final_Mooney": last["Mooney"],
        "max_T_C": float(profile["T_C"].max()),
        "max_Q_rxn_kW": float(profile["Q_rxn_kW"].max()),
        "max_fouling_index": float(profile["fouling_index"].max()),
        "mixing_regime": last["mixing_regime"],
        "recommended_rpm": _recommended_rpm(cfg.rpm, float(profile["fouling_index"].max()), float(profile["impeller_Re"].iloc[-1])),
        "recommendations": dynamic_recommendations(profile, cfg),
    }
    return DynamicReactorResult(config=cfg, profile=profile, stages=stage_timeline(cfg.total_time_min), summary=summary)


def mixing_power(process: ProcessConfig, cfg: DynamicReactorConfig, mu_Pa_s: float) -> dict[str, float | str]:
    """Estimate impeller Reynolds number, power and mixing regime."""
    rho = 680.0
    N = max(cfg.rpm / 60.0, 1.0e-6)
    D = max(cfg.impeller_diameter_m, 0.005)
    V = max(process.reactor_volume_L / 1000.0 * cfg.liquid_fill_fraction, 1.0e-6)
    Re = rho * N * D**2 / max(mu_Pa_s, 1.0e-8)
    base_np = {
        "Rushton turbine": 5.0,
        "pitched blade turbine": 1.5,
        "anchor impeller": 0.8,
        "helical ribbon for high viscosity": 0.35,
        "simple disk turbine": 3.0,
    }.get(cfg.impeller_type, 2.0)
    if Re < 10.0:
        regime = "laminar"
        Np = max(16.0 / max(Re, 1.0e-6), base_np)
    elif Re < 10000.0:
        regime = "transitional"
        Np = base_np * (10000.0 / max(Re, 1.0)) ** 0.12
    else:
        regime = "turbulent"
        Np = base_np
    if cfg.baffles_enabled and regime != "laminar":
        Np *= 1.12
    P_W = Np * rho * N**3 * D**5
    return {
        "mixing_power_kW": P_W / 1000.0,
        "power_per_volume_kW_m3": P_W / 1000.0 / V,
        "impeller_Re": Re,
        "mixing_regime": regime,
        "Np": Np,
    }


def dynamic_recommendations(profile: pd.DataFrame, cfg: DynamicReactorConfig) -> list[str]:
    """Generate practical engineering recommendations from dynamic reactor traces."""
    recs: list[str] = []
    if profile["fouling_index"].max() > 3.0:
        recs.append("动态釜式模型显示挂胶风险高：降低固含或Mw，优先考虑锚式/螺带桨并提高壁面剪切。")
    if profile["T_C"].max() - profile["T_C"].iloc[0] > 20.0:
        recs.append("聚合阶段温升较大：降低催化剂浓度、提高夹套换热面积或采用分段单体/催化剂进料。")
    if profile["C_ENB_mol_L"].std() / max(profile["C_ENB_mol_L"].mean(), TINY) > 0.35:
        recs.append("ENB液相浓度波动较大：建议连续或分段ENB进料，进料点靠近搅拌桨。")
    if profile["impeller_Re"].iloc[-1] < 100.0:
        recs.append("末期搅拌处于层流/低Re：建议改用高黏体系桨型或降低最终固含。")
    if not cfg.baffles_enabled:
        recs.append("无挡板会增强中心涡流并降低径向混合，建议增加挡板验证死区变化。")
    if not recs:
        recs.append("动态釜式模型未显示明显热失控或高挂胶趋势，可进入详细CFD进一步确认局部死区。")
    return recs


def _mode_factor(mode: str, progress: float) -> float:
    if mode.startswith("Fed-batch"):
        return 0.8 + 0.5 * progress
    if mode.startswith("Semi"):
        return 1.0
    if mode.startswith("CSTR"):
        return 0.85
    return 1.0


def _feed_factor(mode: str, gas_feed_mode: str, progress: float) -> float:
    if progress < 0.30 or progress > 0.88:
        return 0.0
    if mode.startswith("Batch") and gas_feed_mode != "恒压补料":
        return 0.05
    if mode.startswith("CSTR"):
        return 1.0
    return 0.65 if gas_feed_mode == "恒压补料" else 0.20


def _transition_factor(mode: str, progress: float) -> float:
    if not mode.startswith("Fed-batch"):
        return 0.0
    return clamp((progress - 0.25) / 0.55, 0.0, 1.0)


def _gas_mole_fractions(process: ProcessConfig, transition: float) -> tuple[float, float, float]:
    e = process.ethylene_kg_h / 28.054 * (1.0 + 0.45 * transition)
    p = process.propylene_kg_h / 42.081 * (1.0 - 0.25 * transition)
    h = max(process.hydrogen_g_h / 1000.0 / 2.016, 1.0e-5)
    total = max(e + p + h, TINY)
    return e / total, p / total, h / total


def _solubility_star(component: str, y_i: float, pressure_MPa: float, T_C: float) -> float:
    return liquid_saturation_concentration_mol_L(component, "hexane", T_C + 273.15, y_i * pressure_MPa)


def _kla(cfg: DynamicReactorConfig, mu_Pa_s: float, component: str) -> float:
    ref = {"ethylene": 28.0, "propylene": 24.0, "hydrogen": 42.0}.get(component, 24.0)
    impeller_factor = {
        "Rushton turbine": 1.15,
        "pitched blade turbine": 1.0,
        "anchor impeller": 0.45,
        "helical ribbon for high viscosity": 0.60,
        "simple disk turbine": 0.85,
    }.get(cfg.impeller_type, 1.0)
    baffle_factor = 1.15 if cfg.baffles_enabled else 0.75
    return ref * (max(cfg.rpm, 1.0) / 500.0) ** 0.72 * (0.001 / max(mu_Pa_s, 1.0e-6)) ** 0.22 * impeller_factor * baffle_factor


def _enb_feed_mol_h(process: ProcessConfig, cfg: DynamicReactorConfig, progress: float, total_time_h: float, comps: dict[str, Any]) -> float:
    total_mol = process.enb_kg_h * total_time_h / (comps["ENB"].MW / 1000.0)
    if cfg.enb_feed_strategy == "一次加入":
        return 0.0
    if cfg.enb_feed_strategy == "连续加入" and 0.32 <= progress <= 0.82:
        return total_mol * 0.75 / max(0.50 * total_time_h, TINY)
    if cfg.enb_feed_strategy == "分段加入" and (0.38 <= progress <= 0.45 or 0.62 <= progress <= 0.68):
        return total_mol * 0.375 / max(0.13 * total_time_h, TINY)
    return 0.0


def _solution_viscosity(T_C: float, solids_wt: float, Mw: float) -> float:
    solids = clamp(solids_wt / 100.0, 0.0, 0.70)
    return clamp(0.00030 * math.exp(8.0 * solids + 15.0 * solids**2) * (Mw / 300000.0) ** 0.6 * math.exp(12000.0 / R_GAS * (1.0 / (T_C + 273.15) - 1.0 / 373.15)), 1.0e-5, 500.0)


def _estimate_mw(N_H2: float, volume_L: float, Mw0: float, T_C: float, progress: float) -> float:
    C_H2 = N_H2 / max(volume_L, TINY)
    thermal = math.exp(-0.004 * (T_C - 100.0))
    age = max(1.0 - 0.18 * progress, 0.55)
    return clamp(Mw0 * thermal * age / (1.0 + 45.0 * C_H2), 50000.0, 1500000.0)


def _effective_U(U0: float, mu: float, solids_wt: float) -> float:
    return max(U0 * (0.001 / max(mu, 1.0e-6)) ** 0.12 * (1.0 - 0.35 * clamp(solids_wt / 35.0, 0.0, 0.85)), U0 * 0.18)


def _fouling_index(solids_wt: float, mu: float, T_C: float) -> float:
    return (solids_wt / 12.0) ** 1.7 * (mu / 0.003) ** 0.28 * math.exp((T_C - 100.0) / 55.0)


def _monomer_mass(N_E: float, N_P: float, N_ENB: float, N_H2: float, comps: dict[str, Any]) -> float:
    return (
        N_E * comps["ethylene"].MW
        + N_P * comps["propylene"].MW
        + N_ENB * comps["ENB"].MW
        + N_H2 * comps["hydrogen"].MW
    ) / 1000.0


def _instant_composition(r_E: float, r_P: float, r_ENB: float, comps: dict[str, Any]) -> dict[str, float]:
    masses = {
        "C2_wt": r_E * comps["ethylene"].MW,
        "C3_wt": r_P * comps["propylene"].MW,
        "ENB_wt": r_ENB * comps["ENB"].MW,
    }
    total = max(sum(masses.values()), TINY)
    return {key: 100.0 * value / total for key, value in masses.items()}


def _stage_name(progress: float) -> str:
    for name, start, end in STAGES:
        if start <= progress <= end:
            return name
    return "聚合反应"


def _recommended_rpm(rpm: float, fouling_max: float, Re_imp: float) -> float:
    target = rpm
    if fouling_max > 3.0:
        target *= 1.18
    if Re_imp < 100.0:
        target *= 1.25
    return clamp(target, 100.0, 1200.0)
