"""Complete EPDM process flowsheet solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import pandas as pd
from pydantic import BaseModel, Field

from .fluid_props import (
    FluidPropertyResult,
    PipeHydraulicsResult,
    calculate_fluid_properties,
    calculate_pipe_hydraulics,
    estimate_stream_volumetric_flow_m3_h,
)
from .heat_balance import HeatBalanceConfig, HeatBalanceResult, calculate_heat_balance
from .components import load_components
from .flash import Flash, FlashResult
from .kinetics import KineticParameters
from .polymer_props import (
    estimate_mooney,
    estimate_tg,
    estimate_tm_and_crystallinity,
    fouling_risk_index,
    generate_recommendations,
    grade_match,
)
from .reactor import ReactorResult, simulate_reactor
from .streams import Stream, mix_streams
from .thermo import mixture_cp_liq
from .utils import c_to_k, data_path, engineering_error_percent, load_yaml, model_dump_compat, mpa_to_pa, positive, safe_divide


class ProcessConfig(BaseModel):
    """User-facing process configuration."""

    temperature_C: float = 100.0
    pressure_MPa: float = 1.0
    reactor_volume_L: float = 5.0
    residence_time_min: float = 30.0
    solvent: str = "hexane"
    solvent_mass_kg_h: float = 100.0
    ethylene_kg_h: float = 20.0
    propylene_kg_h: float = 30.0
    enb_kg_h: float = 3.0
    hydrogen_g_h: float = 5.0
    catalyst_umol_h: float = 100.0
    AlTi_ratio: float = 1000.0
    BHT_ratio: float = 0.0
    num_cstr: int = 2
    reactor_mode: str = "CSTR series"
    flash1_T_C: float = 80.0
    flash1_P_MPa: float = 0.2
    flash2_T_C: float = 140.0
    flash2_P_MPa: float = 0.02
    purge_fraction: float = Field(default=0.05, ge=0.0, le=1.0)
    thermo_mode: str = "Simple Wilson K"
    deltaH_ethylene_kJ_mol: float = -95.0
    deltaH_propylene_kJ_mol: float = -85.0
    deltaH_ENB_kJ_mol: float = -80.0
    heat_transfer_U_W_m2K: float = 300.0
    heat_transfer_area_m2: float = 2.0
    coolant_inlet_C: float = 25.0
    coolant_outlet_C: float = 35.0
    pipe_length_m: float = 20.0
    pipe_diameter_m: float = 0.025
    pipe_roughness_m: float = 0.000045
    pump_efficiency: float = 0.65


@dataclass
class FlowsheetResult:
    """Full process simulation result."""

    config: ProcessConfig
    streams: dict[str, Stream]
    unit_results: dict[str, dict[str, Any]]
    reactor: ReactorResult
    flash1: FlashResult
    flash2: FlashResult
    heat_balance: HeatBalanceResult
    fluid_properties: FluidPropertyResult
    pipe_hydraulics: PipeHydraulicsResult
    kpis: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def stream_table(self) -> pd.DataFrame:
        """Return stream summary table."""
        rows = []
        for name, stream in self.streams.items():
            row = {
                "stream": name,
                "T_C": stream.temperature_K - 273.15,
                "P_MPa": stream.pressure_Pa / 1.0e6,
                "phase": stream.phase,
                "total_kg_h": stream.total_mass_flow(),
                "polymer_kg_h": stream.polymer_mass_kg_h,
                "solids_wt": stream.solids_wt,
            }
            for comp in ["ethylene", "propylene", "ENB", "hydrogen", self.config.solvent]:
                row[f"{comp}_kg_h"] = stream.mass_flows.get(comp, 0.0)
            rows.append(row)
        return pd.DataFrame(rows)

    def unit_table(self) -> pd.DataFrame:
        """Return unit operation result table."""
        rows = []
        for unit, values in self.unit_results.items():
            row = {"unit": unit}
            row.update(values)
            rows.append(row)
        return pd.DataFrame(rows)

    def heat_balance_table(self) -> pd.DataFrame:
        """Return heat-balance report table."""
        return self.heat_balance.as_dataframe()

    def fluid_property_table(self) -> pd.DataFrame:
        """Return fluid-property report table."""
        return self.fluid_properties.as_dataframe()

    def pipe_hydraulics_table(self) -> pd.DataFrame:
        """Return pressure-drop and pumping report table."""
        return self.pipe_hydraulics.as_dataframe()


def load_default_config() -> ProcessConfig:
    """Load default process configuration from YAML."""
    return ProcessConfig(**load_yaml(data_path("default_config.yaml")))


def build_process_graph() -> nx.DiGraph:
    """Return a directed graph for the default EPDM process topology."""
    graph = nx.DiGraph(name="metallocene_epdm_process")
    graph.add_nodes_from(
        [
            "Feed",
            "Mixer",
            "Preheater",
            "Reactor(s)",
            "Quench",
            "Flash-1",
            "Flash-2",
            "Product",
            "Gas recycle",
            "Solvent/ENB recycle",
            "Purge",
        ]
    )
    graph.add_edges_from(
        [
            ("Feed", "Mixer"),
            ("Mixer", "Preheater"),
            ("Preheater", "Reactor(s)"),
            ("Reactor(s)", "Quench"),
            ("Quench", "Flash-1"),
            ("Flash-1", "Flash-2"),
            ("Flash-2", "Product"),
            ("Flash-1", "Gas recycle"),
            ("Flash-2", "Solvent/ENB recycle"),
            ("Gas recycle", "Mixer"),
            ("Solvent/ENB recycle", "Mixer"),
            ("Gas recycle", "Purge"),
            ("Solvent/ENB recycle", "Purge"),
        ]
    )
    return graph


def build_feed_stream(config: ProcessConfig) -> Stream:
    """Build the molecular feed stream from user process inputs."""
    components = load_components()
    solvent = config.solvent if config.solvent in components else "hexane"
    mass_flows = {
        "ethylene": positive(config.ethylene_kg_h),
        "propylene": positive(config.propylene_kg_h),
        "ENB": positive(config.enb_kg_h),
        "hydrogen": positive(config.hydrogen_g_h) / 1000.0,
        solvent: positive(config.solvent_mass_kg_h),
    }
    return Stream.from_mass_flows(
        "Feed",
        temperature_K=298.15,
        pressure_Pa=mpa_to_pa(config.pressure_MPa),
        mass_flows=mass_flows,
        phase="mixed",
        components=components,
    )


def calculate_preheat(inlet: Stream, target_temperature_K: float) -> tuple[Stream, float, float]:
    """Heat mixed feed to reactor temperature and return duty in kJ/h."""
    outlet = inlet.copy_stream("Preheated feed")
    cp = mixture_cp_liq(outlet.mass_flows)
    delta_T = target_temperature_K - inlet.temperature_K
    duty = outlet.total_mass_flow() * cp * delta_T
    outlet.temperature_K = target_temperature_K
    outlet.enthalpy_kJ_h += duty
    return outlet, duty, cp


def quench_reactor(inlet: Stream, config: ProcessConfig) -> tuple[Stream, dict[str, Any]]:
    """Deactivate catalyst and account for a small quench addition."""
    outlet = inlet.copy_stream("Quenched solution")
    quench_agent_kg_h = max(config.catalyst_umol_h * 1.0e-6 * 0.032 * 10.0, 0.0)
    outlet.update_solids()
    return outlet, {"quench_agent_kg_h": quench_agent_kg_h, "active_catalyst": 0.0}


def run_flowsheet(config: ProcessConfig | dict[str, Any] | None = None) -> FlowsheetResult:
    """Run the complete process model from feed to product and recycle summaries."""
    cfg = config if isinstance(config, ProcessConfig) else ProcessConfig(**(config or model_dump_compat(load_default_config())))
    warnings: list[str] = []
    components = load_components()
    if cfg.solvent not in components:
        warnings.append(f"未知溶剂 {cfg.solvent}，已使用 hexane。")
        cfg.solvent = "hexane"
    feed = build_feed_stream(cfg)
    mixed = mix_streams("Mixer outlet", [feed])
    preheated, q_preheat, cp_mix = calculate_preheat(mixed, c_to_k(cfg.temperature_C))
    reactor_result = simulate_reactor(
        preheated,
        temperature_K=c_to_k(cfg.temperature_C),
        pressure_MPa=cfg.pressure_MPa,
        residence_time_min=cfg.residence_time_min,
        reactor_volume_L=cfg.reactor_volume_L,
        catalyst_umol_h=cfg.catalyst_umol_h,
        AlTi_ratio=cfg.AlTi_ratio,
        BHT_ratio=cfg.BHT_ratio,
        mode=cfg.reactor_mode,
        num_cstr=cfg.num_cstr,
        params=KineticParameters(
            dH_E_kJ_mol=cfg.deltaH_ethylene_kJ_mol,
            dH_P_kJ_mol=cfg.deltaH_propylene_kJ_mol,
            dH_ENB_kJ_mol=cfg.deltaH_ENB_kJ_mol,
        ),
    )
    warnings.extend(reactor_result.warnings)
    quenched, quench_result = quench_reactor(reactor_result.outlet, cfg)
    flash1 = Flash("Flash-1", cfg.thermo_mode).calculate(quenched, c_to_k(cfg.flash1_T_C), mpa_to_pa(cfg.flash1_P_MPa))
    flash2 = Flash("Flash-2", cfg.thermo_mode).calculate(flash1.liquid, c_to_k(cfg.flash2_T_C), mpa_to_pa(cfg.flash2_P_MPa))
    product = flash2.liquid.copy_stream("Polymer product")
    product.phase = "polymer solution"
    product.update_solids()
    purge_fraction = cfg.purge_fraction
    flash1_recycle_kg_h = sum(
        flash1.vapor.mass_flows.get(name, 0.0) * (1.0 - purge_fraction)
        for name in ["ethylene", "propylene", "hydrogen"]
    )
    flash2_recycle_kg_h = sum(
        flash2.vapor.mass_flows.get(name, 0.0) * (1.0 - purge_fraction)
        for name in [cfg.solvent, "ENB"]
    )
    purge_kg_h = (flash1.vapor.total_mass_flow() + flash2.vapor.total_mass_flow()) * purge_fraction
    enb_residue_ppm = 1.0e6 * safe_divide(product.mass_flows.get("ENB", 0.0), max(product.polymer_mass_kg_h, 1.0e-9), 0.0)
    comp = reactor_result.polymer_composition_wt
    mooney = estimate_mooney(reactor_result.Mw, reactor_result.PDI, comp["ethylene_wt"], comp["ENB_wt"])
    tg_C = estimate_tg(comp["ethylene_wt"], comp["propylene_wt"], comp["ENB_wt"])
    tm_C, crystallinity = estimate_tm_and_crystallinity(comp["ethylene_wt"], comp["propylene_wt"])
    performance_fouling_index, performance_fouling_level = fouling_risk_index(
        reactor_result.outlet.solids_wt,
        reactor_result.Mw,
        reactor_result.PDI,
        comp["ethylene_wt"],
        c_to_k(cfg.temperature_C),
        mooney,
    )
    fluid_props = calculate_fluid_properties(reactor_result.outlet, reactor_result.Mw)
    mass_holdup_kg = cfg.reactor_volume_L / 1000.0 * fluid_props.liquid_density_kg_m3
    heat_balance = calculate_heat_balance(
        reactor_result.consumed_mol_h,
        mass_holdup_kg=mass_holdup_kg,
        Cp_mix_kJ_kgK=fluid_props.Cp_liq_kJ_kgK,
        preheat_kJ_h=q_preheat,
        devol_kJ_h=flash2.duty_kJ_h,
        sensible_heat_kJ_h=max(q_preheat, 0.0),
        config=HeatBalanceConfig(
            deltaH_polymerization={
                "ethylene": cfg.deltaH_ethylene_kJ_mol,
                "propylene": cfg.deltaH_propylene_kJ_mol,
                "ENB": cfg.deltaH_ENB_kJ_mol,
            },
            overall_U_W_m2K=cfg.heat_transfer_U_W_m2K,
            heat_transfer_area_m2=cfg.heat_transfer_area_m2,
            coolant_inlet_C=cfg.coolant_inlet_C,
            coolant_outlet_C=cfg.coolant_outlet_C,
            reactor_temperature_C=cfg.temperature_C,
        ),
    )
    volumetric_flow_m3_h = estimate_stream_volumetric_flow_m3_h(reactor_result.outlet, fluid_props.liquid_density_kg_m3)
    pipe_hydraulics = calculate_pipe_hydraulics(
        fluid_props.liquid_density_kg_m3,
        fluid_props.dynamic_viscosity_Pa_s,
        volumetric_flow_m3_h,
        cfg.pipe_length_m,
        cfg.pipe_diameter_m,
        cfg.pipe_roughness_m,
        cfg.pump_efficiency,
    )
    mass_in = feed.total_mass_flow()
    mass_out = product.total_mass_flow() + flash1.vapor.total_mass_flow() + flash2.vapor.total_mass_flow()
    closure = engineering_error_percent(mass_in, mass_out)
    product_props = {
        "C2_wt": comp["ethylene_wt"],
        "C3_wt": comp["propylene_wt"],
        "ENB_wt": comp["ENB_wt"],
        "Mooney": mooney,
    }
    grade_scores = {grade: grade_match(product_props, grade) for grade in ["A", "B", "C", "D", "E"]}
    best_grade = max(grade_scores.values(), key=lambda item: item["score"])
    kpis = {
        "polymer_kg_h": reactor_result.polymer_kg_h,
        "catalyst_productivity_g_mol_h": reactor_result.catalyst_productivity_g_mol_h,
        "C2_conversion_pct": reactor_result.conversions["ethylene"],
        "C3_conversion_pct": reactor_result.conversions["propylene"],
        "ENB_conversion_pct": reactor_result.conversions["ENB"],
        "C2_wt": comp["ethylene_wt"],
        "C3_wt": comp["propylene_wt"],
        "ENB_wt": comp["ENB_wt"],
        "Mw": reactor_result.Mw,
        "Mn": reactor_result.Mn,
        "PDI": reactor_result.PDI,
        "Mooney": mooney,
        "Tg_C": tg_C,
        "Tm_C": tm_C,
        "crystallinity": crystallinity,
        "solids_wt": reactor_result.outlet.solids_wt,
        "heat_duty_kJ_h": heat_balance.Q_rxn_kJ_h,
        "heat_duty_kW": heat_balance.Q_rxn_kW,
        "preheat_kJ_h": q_preheat,
        "preheat_kW": heat_balance.preheat_kW,
        "flash1_vapor_fraction": flash1.vapor_fraction,
        "flash2_vapor_fraction": flash2.vapor_fraction,
        "flash1_recycle_kg_h": flash1_recycle_kg_h,
        "flash2_recycle_kg_h": flash2_recycle_kg_h,
        "purge_kg_h": purge_kg_h,
        "ENB_residue_ppm": enb_residue_ppm,
        "devol_duty_kJ_h": flash2.duty_kJ_h,
        "devol_duty_kW": heat_balance.devol_kW,
        "total_cooling_load_kW": heat_balance.Q_cooling_kW,
        "total_utility_kW": heat_balance.total_utility_kW,
        "deltaT_ad_K": heat_balance.deltaT_ad_K,
        "thermal_risk": heat_balance.thermal_risk,
        "Q_max_kW": heat_balance.Q_max_kW,
        "cooling_margin_kW": heat_balance.cooling_margin_kW,
        "heat_transfer_status": heat_balance.heat_transfer_status,
        "fouling_index": fluid_props.fouling_risk_index,
        "fouling_risk": fluid_props.fouling_risk,
        "performance_fouling_index": performance_fouling_index,
        "performance_fouling_risk": performance_fouling_level,
        "mixture_mw_g_mol": fluid_props.mixture_mw_g_mol,
        "liquid_density_kg_m3": fluid_props.liquid_density_kg_m3,
        "gas_density_kg_m3": fluid_props.gas_density_kg_m3,
        "Cp_liq_kJ_kgK": fluid_props.Cp_liq_kJ_kgK,
        "Cp_gas_kJ_kgK": fluid_props.Cp_gas_kJ_kgK,
        "thermal_conductivity_W_mK": fluid_props.thermal_conductivity_W_mK,
        "dynamic_viscosity_Pa_s": fluid_props.dynamic_viscosity_Pa_s,
        "kinematic_viscosity_m2_s": fluid_props.kinematic_viscosity_m2_s,
        "vapor_pressure_Pa": fluid_props.vapor_pressure_Pa,
        "polymer_solution_viscosity_index": fluid_props.polymer_solution_viscosity_index,
        "pipe_Reynolds": pipe_hydraulics.Reynolds,
        "pipe_flow_regime": pipe_hydraulics.flow_regime,
        "pipe_pressure_drop_kPa": pipe_hydraulics.pressure_drop_kPa,
        "pump_power_kW": pipe_hydraulics.pump_power_kW,
        "transport_risk": pipe_hydraulics.transport_risk,
        "mass_balance_error_pct": closure,
        "thermo_mode": flash1.mode,
        "best_grade": best_grade["grade_id"],
        "best_grade_score": best_grade["score"],
    }
    kpis["recommendations"] = generate_recommendations(kpis)
    if abs(closure) > 0.5:
        warnings.append(f"总物料衡算闭合误差 {closure:.2f}%，请检查闪蒸或输入条件。")
    if heat_balance.cooling_margin_kW < 0.0:
        warnings.append("移热能力不足，存在温升和失控风险。")
    if pipe_hydraulics.transport_risk != "normal":
        warnings.append(pipe_hydraulics.transport_risk)
    streams = {
        "Feed": feed,
        "Mixer outlet": mixed,
        "Preheated feed": preheated,
        "Reactor outlet": reactor_result.outlet,
        "Quenched solution": quenched,
        "Flash-1 vapor": flash1.vapor,
        "Flash-1 liquid": flash1.liquid,
        "Flash-2 vapor": flash2.vapor,
        "Polymer product": product,
    }
    unit_results = {
        "Mixer": {"total_kg_h": mixed.total_mass_flow(), "solids_wt": mixed.solids_wt},
        "Preheater": {"Q_preheat_kJ_h": q_preheat, "Cp_mix_kJ_kg_K": cp_mix},
        "Reactor": {
            "Q_rxn_kJ_h": heat_balance.Q_rxn_kJ_h,
            "Q_rxn_kW": heat_balance.Q_rxn_kW,
            "deltaT_ad_K": heat_balance.deltaT_ad_K,
            "thermal_risk": heat_balance.thermal_risk,
            "polymer_kg_h": reactor_result.polymer_kg_h,
            "Cstar_mol_L": reactor_result.Cstar_mol_L,
        },
        "Quench": quench_result,
        "Flash-1": {"vapor_fraction": flash1.vapor_fraction, "duty_kJ_h": flash1.duty_kJ_h},
        "Flash-2": {"vapor_fraction": flash2.vapor_fraction, "duty_kJ_h": flash2.duty_kJ_h},
        "HeatTransfer": {
            "Q_max_kW": heat_balance.Q_max_kW,
            "cooling_margin_kW": heat_balance.cooling_margin_kW,
            "lmtd_K": heat_balance.lmtd_K,
            "status": heat_balance.heat_transfer_status,
        },
        "PipeHydraulics": {
            "Reynolds": pipe_hydraulics.Reynolds,
            "pressure_drop_kPa": pipe_hydraulics.pressure_drop_kPa,
            "pump_power_kW": pipe_hydraulics.pump_power_kW,
            "risk": pipe_hydraulics.transport_risk,
        },
        "Recycle": {
            "flash1_recycle_kg_h": flash1_recycle_kg_h,
            "flash2_recycle_kg_h": flash2_recycle_kg_h,
            "purge_kg_h": purge_kg_h,
            "mass_balance_error_pct": closure,
        },
    }
    return FlowsheetResult(
        config=cfg,
        streams=streams,
        unit_results=unit_results,
        reactor=reactor_result,
        flash1=flash1,
        flash2=flash2,
        heat_balance=heat_balance,
        fluid_properties=fluid_props,
        pipe_hydraulics=pipe_hydraulics,
        kpis=kpis,
        warnings=warnings,
    )
