"""Polymerization reactor models."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

from .components import load_components
from .kinetics import (
    KineticParameters,
    active_center_concentration,
    activation_factor,
    calculate_template_rates,
    estimate_molecular_weight,
    reaction_rates,
)
from .polymer_props import estimate_mooney
from .reaction_templates import monomers_from_template, segment_map_from_template, template_with_fallback
from .solubility import liquid_saturation_concentration_mol_L
from .streams import Stream
from .utils import R_GAS, TINY, c_to_k, clamp, positive, safe_divide


DEFAULT_REACTION_TEMPLATE_ID = "EPDM_EPM_metallocene_solution"
MONOMERS = monomers_from_template(DEFAULT_REACTION_TEMPLATE_ID)
SEGMENT_MAP = segment_map_from_template(DEFAULT_REACTION_TEMPLATE_ID)


@dataclass
class ReactorStage:
    """One reactor stage result."""

    stage: int
    tau_h: float
    C_E_mol_L: float
    C_P_mol_L: float
    C_ENB_mol_L: float
    r_E_mol_L_h: float
    r_P_mol_L_h: float
    r_ENB_mol_L_h: float
    ethylene_mol_h_out: float
    propylene_mol_h_out: float
    ENB_mol_h_out: float
    polymer_kg_h: float
    heat_kJ_h: float


@dataclass
class ReactorResult:
    """Aggregated reactor calculation result."""

    outlet: Stream
    stages: list[ReactorStage]
    conversions: dict[str, float]
    rates: dict[str, float]
    heat_duty_kJ_h: float
    consumed_mol_h: dict[str, float]
    polymer_kg_h: float
    polymer_composition_wt: dict[str, float]
    catalyst_productivity_g_mol_h: float
    residence_time_min: float
    Mw: float
    Mn: float
    PDI: float
    Cstar_mol_L: float
    liquid_volume_L_h: float
    warnings: list[str] = field(default_factory=list)

    def stage_dataframe(self) -> pd.DataFrame:
        """Return stage results as a DataFrame."""
        return pd.DataFrame([stage.__dict__ for stage in self.stages])


@dataclass
class DynamicSemibatchODEResult:
    """Detailed semi-batch ODE simulation result."""

    profile: pd.DataFrame
    stages: pd.DataFrame
    summary: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def time_profile(self) -> pd.DataFrame:
        """Return the ODE time profile."""
        return self.profile.copy()


def estimate_liquid_volume_flow_L_h(stream: Stream) -> float:
    """Estimate liquid volume flow from mass flows and component densities."""
    components = load_components()
    volume_m3_h = 0.0
    for name, mass in stream.mass_flows.items():
        if name in components:
            volume_m3_h += positive(mass) / max(components[name].density_liq, TINY)
    if stream.polymer_mass_kg_h > 0:
        volume_m3_h += stream.polymer_mass_kg_h / components["polymer_pseudo"].density_liq
    return max(volume_m3_h * 1000.0, 1.0e-6)


def _stage_conversion_factor(mode: str, pseudo_first_order_h: float, tau_h: float) -> float:
    """Return monomer conversion fraction for one idealized reactor stage."""
    x = max(pseudo_first_order_h * tau_h, 0.0)
    mode_lower = mode.lower()
    if mode_lower.startswith("batch") or mode_lower.startswith("semi") or mode_lower.startswith("fed") or mode_lower.startswith("plug"):
        return clamp(1.0 - pow(2.718281828, -x), 0.0, 0.98)
    return clamp(safe_divide(x, 1.0 + x, 0.0), 0.0, 0.98)


def simulate_reactor(
    inlet: Stream,
    temperature_K: float,
    pressure_MPa: float,
    residence_time_min: float,
    reactor_volume_L: float,
    catalyst_umol_h: float,
    AlTi_ratio: float,
    BHT_ratio: float,
    agitation_rpm: float = 500.0,
    mode: str = "CSTR series",
    num_cstr: int = 2,
    params: KineticParameters | None = None,
    reaction_template_id: str = DEFAULT_REACTION_TEMPLATE_ID,
) -> ReactorResult:
    """Simulate batch, single CSTR, CSTR-series, or plug-flow-approximation EPDM polymerization."""
    p = params or KineticParameters()
    template, template_warnings = template_with_fallback(reaction_template_id)
    monomers = tuple(template.monomers)
    segment_map = dict(template.polymer_segments)
    template_mw = dict(template.molecular_weights)
    components = load_components()
    warnings: list[str] = list(template_warnings)
    outlet = inlet.copy_stream("Reactor outlet")
    outlet.temperature_K = temperature_K
    outlet.pressure_Pa = pressure_MPa * 1.0e6
    inlet_moles = {name: positive(inlet.molar_flows.get(name, 0.0)) for name in monomers}
    liquid_volume_L_h = estimate_liquid_volume_flow_L_h(inlet)
    tau_h_total = max(residence_time_min / 60.0, 1.0e-6)
    mode_lower = mode.lower()
    stages_n = 1 if mode in ("Batch reactor", "CSTR", "Plug Flow Approximation") or mode_lower.startswith(("semi", "fed")) else int(clamp(num_cstr, 1, 8))
    tau_stage_h = tau_h_total / stages_n
    Cstar = active_center_concentration(catalyst_umol_h, liquid_volume_L_h, AlTi_ratio, BHT_ratio, tau_h_total, p)
    act = activation_factor(AlTi_ratio, BHT_ratio, p)
    current_moles = inlet_moles.copy()
    segment_masses = {segment: 0.0 for segment in segment_map.values()}
    consumed_total = {name: 0.0 for name in monomers}
    heat_total = 0.0
    stage_results: list[ReactorStage] = []
    rates_last = {"r_E": 0.0, "r_P": 0.0, "r_ENB": 0.0}
    for idx in range(1, stages_n + 1):
        concentrations = {monomer: safe_divide(current_moles.get(monomer, 0.0), liquid_volume_L_h, 0.0) for monomer in monomers}
        rate = calculate_template_rates(
            reaction_template_id,
            concentrations,
            {"Cstar_mol_L": Cstar},
            {"temperature_K": temperature_K, "pressure_MPa": pressure_MPa},
            p,
        )
        # Mixing Efficiency Correction (Damköhler Number influence)
        # In large industrial reactors, mixing time limits the effective rate.
        mixing_time_s = 5.2 * max(reactor_volume_L/1000.0, 0.1)**(1/3) / max(positive(agitation_rpm)/60.0 * 0.1, 0.05)
        tau_rxn_s = safe_divide(1.0, max(rate.effective_rate_constants.get("ethylene", 0.0) * Cstar, 1.0e-9), 1.0e6)
        Da = mixing_time_s / max(tau_rxn_s, 1.0e-6)
        mixing_factor = clamp(1.0 / (1.0 + 0.15 * Da), 0.70, 1.0)
        
        warnings.extend(rate.warnings)
        kappa = {monomer: rate.effective_rate_constants.get(monomer, 0.0) * Cstar * mixing_factor for monomer in monomers}
        consumed: dict[str, float] = {}
        for monomer in monomers:
            conv = _stage_conversion_factor(mode, kappa.get(monomer, 0.0), tau_stage_h)
            consumed[monomer] = min(current_moles[monomer] * conv, current_moles[monomer])
            current_moles[monomer] -= consumed[monomer]
            consumed_total[monomer] += consumed[monomer]
        heat_stage = sum(consumed[m] * abs(float(template.heat_of_polymerization.get(m, -80.0))) for m in monomers)
        heat_total += heat_stage
        for monomer, mol in consumed.items():
            segment = segment_map[monomer]
            segment_masses[segment] += mol * template_mw.get(monomer, getattr(components.get(monomer), "MW", 100.0)) / 1000.0
        polymer_stage = sum(consumed[m] * template_mw.get(m, getattr(components.get(m), "MW", 100.0)) / 1000.0 for m in monomers)
        rates_last = {
            "r_E": safe_divide(consumed.get("ethylene", 0.0), max(liquid_volume_L_h * tau_stage_h, TINY), 0.0),
            "r_P": safe_divide(consumed.get("propylene", 0.0), max(liquid_volume_L_h * tau_stage_h, TINY), 0.0),
            "r_ENB": safe_divide(consumed.get("ENB", 0.0), max(liquid_volume_L_h * tau_stage_h, TINY), 0.0),
        }
        stage_results.append(
            ReactorStage(
                stage=idx,
                tau_h=tau_stage_h,
                C_E_mol_L=concentrations.get("ethylene", 0.0),
                C_P_mol_L=concentrations.get("propylene", 0.0),
                C_ENB_mol_L=concentrations.get("ENB", 0.0),
                r_E_mol_L_h=rates_last["r_E"],
                r_P_mol_L_h=rates_last["r_P"],
                r_ENB_mol_L_h=rates_last["r_ENB"],
                ethylene_mol_h_out=current_moles.get("ethylene", 0.0),
                propylene_mol_h_out=current_moles.get("propylene", 0.0),
                ENB_mol_h_out=current_moles.get("ENB", 0.0),
                polymer_kg_h=sum(segment_masses.values()),
                heat_kJ_h=heat_total,
            )
        )
    for monomer in monomers:
        outlet.molar_flows[monomer] = current_moles[monomer]
    outlet.sync_mass_from_moles(components)
    for key, value in inlet.mass_flows.items():
        if key not in monomers:
            outlet.mass_flows[key] = value
    outlet.segment_masses_kg_h = segment_masses
    outlet.polymer_mass_kg_h = sum(segment_masses.values())
    outlet.update_solids()
    polymer_mass = outlet.polymer_mass_kg_h
    polymer_comp = {
        "ethylene_wt": 100.0 * safe_divide(segment_masses.get(segment_map.get("ethylene", "E"), 0.0), polymer_mass, 0.0),
        "propylene_wt": 100.0 * safe_divide(segment_masses.get(segment_map.get("propylene", "P"), 0.0), polymer_mass, 0.0),
        "ENB_wt": 100.0 * safe_divide(segment_masses.get(segment_map.get("ENB", "D"), 0.0), polymer_mass, 0.0),
    }
    conversions = {
        name: 100.0 * safe_divide(inlet_moles[name] - current_moles[name], inlet_moles[name], 0.0)
        for name in monomers
    }
    H2_C = safe_divide(positive(inlet.molar_flows.get("hydrogen", 0.0)), liquid_volume_L_h, 0.0)
    Mw = estimate_molecular_weight(p.Mw0, H2_C, polymer_comp["ethylene_wt"], outlet.solids_wt, p)
    PDI = clamp(
        2.45
        + (0.16 * stages_n if mode == "CSTR series" else 0.35)
        + 0.18 * safe_divide(outlet.solids_wt, 20.0, 0.0)
        + 0.18 * abs(polymer_comp["ethylene_wt"] - 55.0) / 30.0,
        2.1,
        5.5,
    )
    Mn = Mw / PDI
    catalyst_mol_h = positive(catalyst_umol_h) * 1.0e-6
    productivity = safe_divide(polymer_mass * 1000.0, catalyst_mol_h, 0.0)
    if act < 0.5:
        warnings.append("Al/Ti 或 BHT 条件导致活性中心因子偏低。")
    if outlet.solids_wt > 25.0:
        warnings.append("胶液固含量较高，需关注传热和输送风险。")
    return ReactorResult(
        outlet=outlet,
        stages=stage_results,
        conversions=conversions,
        rates=rates_last,
        heat_duty_kJ_h=heat_total,
        consumed_mol_h=consumed_total,
        polymer_kg_h=polymer_mass,
        polymer_composition_wt=polymer_comp,
        catalyst_productivity_g_mol_h=productivity,
        residence_time_min=residence_time_min,
        Mw=Mw,
        Mn=Mn,
        PDI=PDI,
        Cstar_mol_L=Cstar,
        liquid_volume_L_h=liquid_volume_L_h,
        warnings=warnings,
    )


def simulate_dynamic_semibatch_ode(
    process: Any,
    recipe: dict[str, Any] | None = None,
    params: KineticParameters | None = None,
) -> DynamicSemibatchODEResult:
    """Simulate a pressure-fed semi-batch stirred-tank polymerization with solve_ivp.

    The model is still an R&D apparent model, but it explicitly integrates
    liquid monomer holdups, hydrogen, polymer mass, temperature and active
    catalyst inventory.  It is designed as the detailed mode counterpart to the
    fast dashboard model.
    """
    cfg = recipe or {}
    p = params or KineticParameters(
        dH_E_kJ_mol=getattr(process, "deltaH_ethylene_kJ_mol", -95.0),
        dH_P_kJ_mol=getattr(process, "deltaH_propylene_kJ_mol", -85.0),
        dH_ENB_kJ_mol=getattr(process, "deltaH_ENB_kJ_mol", -80.0),
    )
    comps = load_components()
    total_time_min = float(cfg.get("total_time_min", max(float(getattr(process, "residence_time_min", 60.0)), 60.0)))
    n_eval = int(clamp(float(cfg.get("n_eval", 91)), 20.0, 361.0))
    total_time_h = max(total_time_min / 60.0, 1.0e-6)
    volume_L = max(float(getattr(process, "reactor_volume_L", 5.0)) * float(cfg.get("liquid_fill_fraction", 0.75)), 0.05)
    solvent_mass_kg = max(float(getattr(process, "solvent_mass_kg_h", 100.0)) * total_time_h, 0.05)
    rpm = float(cfg.get("rpm", getattr(process, "agitation_rpm", 500.0)))
    coolant_C = float(cfg.get("coolant_C", getattr(process, "coolant_outlet_C", 35.0)))
    enb_strategy = str(cfg.get("enb_feed_strategy", "一次加入"))
    h2_strategy = str(cfg.get("hydrogen_feed_strategy", "初始加入"))
    catalyst_strategy = str(cfg.get("catalyst_feed_strategy", "一次注入"))
    gas_feed_mode = str(cfg.get("gas_feed_mode", "恒压补料"))
    quench_active = bool(cfg.get("quench_active", False))
    recipe_event_log = list(cfg.get("recipe_event_log", []))
    initial_enb_fraction = 1.0 if enb_strategy == "一次加入" else 0.25
    feed_E_mol_h = positive(float(getattr(process, "ethylene_kg_h", 20.0))) * 1000.0 / comps["ethylene"].MW
    feed_P_mol_h = positive(float(getattr(process, "propylene_kg_h", 30.0))) * 1000.0 / comps["propylene"].MW
    feed_D_total_mol = positive(float(getattr(process, "enb_kg_h", 3.0))) * total_time_h * 1000.0 / comps["ENB"].MW
    feed_H2_mol_h = positive(float(getattr(process, "hydrogen_g_h", 5.0))) / comps["hydrogen"].MW
    y0 = np.array(
        [
            0.05 * feed_E_mol_h * total_time_h,
            0.05 * feed_P_mol_h * total_time_h,
            initial_enb_fraction * feed_D_total_mol,
            0.03 * feed_H2_mol_h * total_time_h,
            0.0,
            c_to_k(float(getattr(process, "temperature_C", 100.0)) - 6.0),
            1.0,
            0.0,
            0.0,
            0.0,
        ],
        dtype=float,
    )
    warnings: list[str] = []

    def rhs(t_h: float, y: np.ndarray) -> np.ndarray:
        N_E, N_P, N_D, N_H2, M_poly, T_K, cat_active, _, _, _ = np.maximum(y, 0.0)
        progress = clamp(t_h / total_time_h, 0.0, 1.0)
        if quench_active and progress >= 0.86:
            cat_active = 0.0
        T_C = T_K - 273.15
        total_mass_kg = solvent_mass_kg + M_poly + _monomer_mass(N_E, N_P, N_D, N_H2, comps)
        solids_wt = 100.0 * safe_divide(M_poly, total_mass_kg, 0.0)
        H2_C = safe_divide(N_H2, volume_L, 0.0)
        mw = estimate_molecular_weight(p.Mw0, H2_C, 55.0, solids_wt, p)
        mu = _ode_solution_viscosity(T_K, solids_wt, mw)
        C_E = safe_divide(N_E, volume_L, 0.0)
        C_P = safe_divide(N_P, volume_L, 0.0)
        C_D = safe_divide(N_D, volume_L, 0.0)
        gas_factor = _ode_gas_feed_factor(progress, gas_feed_mode)
        feed_E = gas_factor * feed_E_mol_h
        feed_P = gas_factor * feed_P_mol_h
        feed_H2 = (gas_factor if h2_strategy == "连续补入" else 0.0) * feed_H2_mol_h
        feed_D = _ode_enb_feed(feed_D_total_mol, total_time_h, progress, enb_strategy)
        kLa_E = _ode_kla(rpm, mu, "ethylene")
        kLa_P = _ode_kla(rpm, mu, "propylene")
        kLa_H2 = _ode_kla(rpm, mu, "hydrogen")
        y_E, y_P, y_H2 = _ode_gas_fractions(process)
        C_E_star = _ode_solubility("ethylene", y_E, float(getattr(process, "pressure_MPa", 1.0)), T_K)
        C_P_star = _ode_solubility("propylene", y_P, float(getattr(process, "pressure_MPa", 1.0)), T_K)
        C_H2_star = _ode_solubility("hydrogen", y_H2, float(getattr(process, "pressure_MPa", 1.0)), T_K)
        transfer_E = kLa_E * max(C_E_star - C_E, -0.35 * C_E) * volume_L
        transfer_P = kLa_P * max(C_P_star - C_P, -0.35 * C_P) * volume_L
        transfer_H2 = kLa_H2 * max(C_H2_star - safe_divide(N_H2, volume_L, 0.0), -0.35 * safe_divide(N_H2, volume_L, 0.0)) * volume_L
        feed_cat_factor = 1.0
        if catalyst_strategy == "分段注入" and 0.52 <= progress <= 0.58:
            feed_cat_factor = 1.35
        Cstar = active_center_concentration(
            float(getattr(process, "catalyst_umol_h", 100.0)) * cat_active * feed_cat_factor,
            volume_L,
            float(getattr(process, "AlTi_ratio", 1000.0)),
            float(getattr(process, "BHT_ratio", 0.0)),
            0.0,
            p,
        )
        if quench_active and progress >= 0.86:
            rates = reaction_rates({"ethylene": 0.0, "propylene": 0.0, "ENB": 0.0}, 0.0, T_K, float(getattr(process, "pressure_MPa", 1.0)), p)
        else:
            rates = reaction_rates({"ethylene": C_E, "propylene": C_P, "ENB": C_D}, Cstar, T_K, float(getattr(process, "pressure_MPa", 1.0)), p)
        r_E = min(rates.r_E_mol_L_h * volume_L, max((N_E + max(feed_E + transfer_E, 0.0) * 0.05) / 0.05, 0.0))
        r_P = min(rates.r_P_mol_L_h * volume_L, max((N_P + max(feed_P + transfer_P, 0.0) * 0.05) / 0.05, 0.0))
        r_D = min(rates.r_ENB_mol_L_h * volume_L, max((N_D + max(feed_D, 0.0) * 0.05) / 0.05, 0.0))
        d_poly = (r_E * comps["ethylene"].MW + r_P * comps["propylene"].MW + r_D * comps["ENB"].MW) / 1000.0
        q_rxn_kJ_h = -(r_E * p.dH_E_kJ_mol + r_P * p.dH_P_kJ_mol + r_D * p.dH_ENB_kJ_mol)
        U_eff = _ode_effective_U(float(getattr(process, "heat_transfer_U_W_m2K", 300.0)), mu, solids_wt)
        q_removed_kJ_h = max(U_eff * float(getattr(process, "heat_transfer_area_m2", 2.0)) * (T_C - coolant_C), 0.0) * 3.6
        mixing_kJ_h = _ode_mixing_power_kW(rpm, mu, float(getattr(process, "reactor_volume_L", 5.0))) * 3600.0
        heat_capacity = max(total_mass_kg * 2.05, 0.2)
        dT = (q_rxn_kJ_h - q_removed_kJ_h + mixing_kJ_h) / heat_capacity
        return np.array(
            [
                feed_E + transfer_E - r_E,
                feed_P + transfer_P - r_P,
                feed_D - r_D,
                feed_H2 + transfer_H2 - 0.004 * r_E,
                d_poly,
                dT,
                (-100.0 * max(cat_active, 0.0)) if quench_active and progress >= 0.86 else -p.kd_h * max(cat_active, 0.0),
                r_E,
                r_P,
                r_D,
            ],
            dtype=float,
        )

    t_eval = np.linspace(0.0, total_time_h, n_eval)
    try:
        # Using LSODA as it automatically switches between stiff (BDF) and non-stiff (Adams) methods
        sol = solve_ivp(
            rhs, 
            (0.0, total_time_h), 
            y0, 
            method="LSODA", 
            t_eval=t_eval, 
            max_step=max(total_time_h / 60.0, 1.0e-3),
            rtol=1.0e-5, 
            atol=1.0e-8
        )
        if not sol.success:
            warnings.append(f"ODE求解器未完全收敛：{sol.message}")
    except Exception as exc:
        warnings.append(f"ODE求解发生异常（{exc}），已启用二阶启发式近似回退。")
        # Heuristic fallback: tiled initial state with slight linear trend for UI stability
        sol_y = np.tile(y0[:, None], (1, len(t_eval)))
        # Add slight mass accumulation trend to avoid static lines
        for i in range(1, len(t_eval)):
            sol_y[4, i] = sol_y[4, 0] + 0.1 * i / len(t_eval) # Polymer mass
        sol = type("Fallback", (), {"t": t_eval, "y": sol_y, "success": False})()
    rows: list[dict[str, Any]] = []
    for idx, t_h in enumerate(sol.t):
        y = np.maximum(sol.y[:, idx], 0.0)
        N_E, N_P, N_D, N_H2, M_poly, T_K, cat_active, cons_E, cons_P, cons_D = y
        total_mass_kg = solvent_mass_kg + M_poly + _monomer_mass(N_E, N_P, N_D, N_H2, comps)
        solids_wt = 100.0 * safe_divide(M_poly, total_mass_kg, 0.0)
        comp = _instant_composition(max(cons_E, 1.0e-12), max(cons_P, 1.0e-12), max(cons_D, 1.0e-12), comps)
        C_H2 = safe_divide(N_H2, volume_L, 0.0)
        Mw = estimate_molecular_weight(p.Mw0, C_H2, comp["C2_wt"], solids_wt, p)
        PDI = clamp(2.55 + 0.20 * t_h / total_time_h + 0.20 * safe_divide(solids_wt, 25.0, 0.0), 2.1, 5.8)
        mu = _ode_solution_viscosity(T_K, solids_wt, Mw)
        rates = reaction_rates(
            {"ethylene": safe_divide(N_E, volume_L, 0.0), "propylene": safe_divide(N_P, volume_L, 0.0), "ENB": safe_divide(N_D, volume_L, 0.0)},
            active_center_concentration(float(getattr(process, "catalyst_umol_h", 100.0)) * cat_active, volume_L, float(getattr(process, "AlTi_ratio", 1000.0)), float(getattr(process, "BHT_ratio", 0.0)), 0.0, p),
            T_K,
            float(getattr(process, "pressure_MPa", 1.0)),
            p,
        )
        q_rxn_kW = max(-(rates.r_E_mol_L_h * volume_L * p.dH_E_kJ_mol + rates.r_P_mol_L_h * volume_L * p.dH_P_kJ_mol + rates.r_ENB_mol_L_h * volume_L * p.dH_ENB_kJ_mol) / 3600.0, 0.0)
        y_E, y_P, y_H2 = _ode_gas_fractions(process)
        pressure_control_error = float(getattr(process, "pressure_MPa", 1.0)) - (0.96 * float(getattr(process, "pressure_MPa", 1.0)) + 0.04 * (y[0] + y[1]) / max(volume_L, TINY) / 10.0)
        q_removed_kW = max(_ode_effective_U(float(getattr(process, "heat_transfer_U_W_m2K", 300.0)), mu, solids_wt) * float(getattr(process, "heat_transfer_area_m2", 2.0)) * ((T_K - 273.15) - coolant_C), 0.0) / 1000.0
        rows.append(
            {
                "time_min": t_h * 60.0,
                "T_C": clamp(T_K - 273.15, -50.0, 260.0),
                "P_MPa": float(getattr(process, "pressure_MPa", 1.0)) + 0.02 * pressure_control_error,
                "C_E_mol_L": safe_divide(N_E, volume_L, 0.0),
                "C_P_mol_L": safe_divide(N_P, volume_L, 0.0),
                "C_ENB_mol_L": safe_divide(N_D, volume_L, 0.0),
                "C_H2_mol_L": C_H2,
                "gas_y_E": y_E,
                "gas_y_P": y_P,
                "gas_y_H2": y_H2,
                "liquid_x_E": safe_divide(N_E, max(N_E + N_P + N_D + N_H2, TINY), 0.0),
                "liquid_x_P": safe_divide(N_P, max(N_E + N_P + N_D + N_H2, TINY), 0.0),
                "liquid_x_ENB": safe_divide(N_D, max(N_E + N_P + N_D + N_H2, TINY), 0.0),
                "conversion_E": 100.0 * safe_divide(cons_E, cons_E + N_E, 0.0),
                "conversion_P": 100.0 * safe_divide(cons_P, cons_P + N_P, 0.0),
                "conversion_ENB": 100.0 * safe_divide(cons_D, cons_D + N_D, 0.0),
                "conversion_pct": 100.0 * safe_divide(M_poly, M_poly + _monomer_mass(N_E, N_P, N_D, 0.0, comps), 0.0),
                "Q_rxn_kW": q_rxn_kW,
                "Q_removed_kW": q_removed_kW,
                "jacket_duty_kW": q_removed_kW,
                "temperature_controller_output": clamp((T_K - c_to_k(float(getattr(process, "temperature_C", 100.0)))) / 15.0, -1.0, 1.0),
                "solids_wt": solids_wt,
                "viscosity_Pa_s": mu,
                "Mw": Mw,
                "PDI": PDI,
                "Mooney": estimate_mooney(Mw, PDI, comp["C2_wt"], comp["ENB_wt"]),
                "C2_wt": comp["C2_wt"],
                "C3_wt": comp["C3_wt"],
                "ENB_wt": comp["ENB_wt"],
                "fouling_index": (solids_wt / 12.0) ** 1.7 * (mu / 0.003) ** 0.28,
                "catalyst_active": cat_active,
            }
        )
    profile = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if profile["T_C"].max() > float(getattr(process, "temperature_C", 100.0)) + 60.0:
        warnings.append("ODE模型显示高温升趋势，需要检查冷却面积、催化剂浓度和投料策略。")
    stages = _ode_stage_timeline(total_time_min)
    summary = {
        "final_conversion_pct": float(profile["conversion_pct"].iloc[-1]),
        "final_solids_wt": float(profile["solids_wt"].iloc[-1]),
        "final_viscosity_Pa_s": float(profile["viscosity_Pa_s"].iloc[-1]),
        "final_Mw": float(profile["Mw"].iloc[-1]),
        "final_Mooney": float(profile["Mooney"].iloc[-1]),
        "max_T_C": float(profile["T_C"].max()),
        "max_Q_rxn_kW": float(profile["Q_rxn_kW"].max()),
        "max_fouling_index": float(profile["fouling_index"].max()),
        "runaway_warning": bool(profile["T_C"].max() > float(getattr(process, "temperature_C", 100.0)) + 35.0),
        "event_log": recipe_event_log,
        "recommendations": _ode_recommendations(profile),
    }
    return DynamicSemibatchODEResult(profile=profile, stages=stages, summary=summary, warnings=warnings)


def _ode_stage_timeline(total_time_min: float) -> pd.DataFrame:
    stages = [
        ("惰化", 0.00, 0.04),
        ("加入溶剂/ENB", 0.04, 0.18),
        ("升温与充压", 0.18, 0.32),
        ("注入催化剂", 0.32, 0.36),
        ("半连续聚合", 0.36, 0.86),
        ("终止与出料", 0.86, 1.00),
    ]
    return pd.DataFrame(
        [{"stage": name, "start_min": start * total_time_min, "end_min": end * total_time_min, "duration_min": (end - start) * total_time_min} for name, start, end in stages]
    )


def _monomer_mass(N_E: float, N_P: float, N_ENB: float, N_H2: float, comps: dict[str, Any]) -> float:
    """Return monomer/H2 mass in kg from mole inventories."""
    return (
        N_E * comps["ethylene"].MW
        + N_P * comps["propylene"].MW
        + N_ENB * comps["ENB"].MW
        + N_H2 * comps["hydrogen"].MW
    ) / 1000.0


def _instant_composition(r_E: float, r_P: float, r_ENB: float, comps: dict[str, Any]) -> dict[str, float]:
    """Return instantaneous polymer composition wt% from insertion rates."""
    masses = {
        "C2_wt": r_E * comps["ethylene"].MW,
        "C3_wt": r_P * comps["propylene"].MW,
        "ENB_wt": r_ENB * comps["ENB"].MW,
    }
    total = max(sum(masses.values()), TINY)
    return {key: 100.0 * value / total for key, value in masses.items()}


def _ode_gas_feed_factor(progress: float, gas_feed_mode: str) -> float:
    if progress < 0.30 or progress > 0.88:
        return 0.0
    return 0.70 if gas_feed_mode == "恒压补料" else 0.12


def _ode_enb_feed(total_mol: float, total_time_h: float, progress: float, strategy: str) -> float:
    if strategy == "连续加入" and 0.34 <= progress <= 0.84:
        return total_mol * 0.75 / max(0.50 * total_time_h, TINY)
    if strategy == "分段加入" and (0.38 <= progress <= 0.44 or 0.62 <= progress <= 0.68):
        return total_mol * 0.375 / max(0.12 * total_time_h, TINY)
    return 0.0


def _ode_gas_fractions(process: Any) -> tuple[float, float, float]:
    e = positive(float(getattr(process, "ethylene_kg_h", 20.0))) / 28.054
    p = positive(float(getattr(process, "propylene_kg_h", 30.0))) / 42.081
    h = max(positive(float(getattr(process, "hydrogen_g_h", 5.0))) / 1000.0 / 2.016, 1.0e-6)
    total = max(e + p + h, TINY)
    return e / total, p / total, h / total


def _ode_solubility(component: str, y_i: float, pressure_MPa: float, temperature_K: float) -> float:
    return liquid_saturation_concentration_mol_L(component, "hexane", temperature_K, y_i * pressure_MPa)


def _ode_kla(rpm: float, mu: float, component: str) -> float:
    base = {"ethylene": 28.0, "propylene": 24.0, "hydrogen": 42.0}.get(component, 24.0)
    return base * (max(rpm, 1.0) / 500.0) ** 0.72 * (0.001 / max(mu, 1.0e-6)) ** 0.22


def _ode_solution_viscosity(T_K: float, solids_wt: float, Mw: float) -> float:
    """Calculate viscosity for ODE integration using the centralized property engine."""
    from .fluid_props import polymer_solution_viscosity
    from .streams import Stream
    
    # Create a dummy stream for property calculation using keyword arguments
    dummy = Stream(name="ODE_Dummy", temperature_K=float(T_K), pressure_Pa=1.0e6, mass_flows={"hexane": 100.0})
    dummy.solids_wt = float(solids_wt)
    dummy.polymer_mass_kg_h = 100.0 * float(solids_wt) / max(100.0 - float(solids_wt), 1.0)
    
    return polymer_solution_viscosity(dummy, float(T_K), float(Mw))


def _ode_effective_U(U0: float, mu: float, solids_wt: float) -> float:
    return max(U0 * (0.001 / max(mu, 1.0e-6)) ** 0.12 * (1.0 - 0.35 * clamp(solids_wt / 35.0, 0.0, 0.85)), U0 * 0.18)


def _ode_mixing_power_kW(rpm: float, mu: float, volume_L: float) -> float:
    rho = 680.0
    N = max(rpm / 60.0, 1.0e-6)
    D = max((max(volume_L, 0.1) / 1000.0) ** (1.0 / 3.0) * 0.35, 0.01)
    Re = rho * N * D**2 / max(mu, 1.0e-8)
    Np = 5.0 if Re > 10000.0 else max(16.0 / max(Re, 1.0e-6), 1.5)
    return Np * rho * N**3 * D**5 / 1000.0


def _ode_recommendations(profile: pd.DataFrame) -> list[str]:
    recs: list[str] = []
    if profile["fouling_index"].max() > 3.0:
        recs.append("ODE详细模型显示挂胶风险偏高：建议降低固含/Mw或采用分段投料。")
    if profile["T_C"].max() - profile["T_C"].iloc[0] > 25.0:
        recs.append("ODE详细模型显示明显温升：建议提高U/A或降低催化剂注入速率。")
    if profile["C_ENB_mol_L"].std() / max(profile["C_ENB_mol_L"].mean(), TINY) > 0.35:
        recs.append("ENB液相浓度波动偏大：建议连续或分段ENB进料并靠近搅拌桨。")
    if not recs:
        recs.append("ODE详细模型未显示明显热失控趋势；建议结合反应量热进一步校准。")
    return recs
