"""Polymerization reactor models."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .components import load_components
from .kinetics import (
    KineticParameters,
    active_center_concentration,
    activation_factor,
    estimate_molecular_weight,
    reaction_rates,
)
from .streams import Stream
from .utils import TINY, clamp, positive, safe_divide


MONOMERS = ("ethylene", "propylene", "ENB")
SEGMENT_MAP = {"ethylene": "E", "propylene": "P", "ENB": "D"}


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
    if mode.lower().startswith("batch"):
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
    mode: str = "CSTR series",
    num_cstr: int = 2,
    params: KineticParameters | None = None,
) -> ReactorResult:
    """Simulate batch, single CSTR, or CSTR-series EPDM polymerization."""
    p = params or KineticParameters()
    components = load_components()
    warnings: list[str] = []
    outlet = inlet.copy_stream("Reactor outlet")
    outlet.temperature_K = temperature_K
    outlet.pressure_Pa = pressure_MPa * 1.0e6
    inlet_moles = {name: positive(inlet.molar_flows.get(name, 0.0)) for name in MONOMERS}
    liquid_volume_L_h = estimate_liquid_volume_flow_L_h(inlet)
    tau_h_total = max(residence_time_min / 60.0, 1.0e-6)
    stages_n = 1 if mode in ("Batch reactor", "CSTR") else int(clamp(num_cstr, 1, 8))
    tau_stage_h = tau_h_total / stages_n
    Cstar = active_center_concentration(catalyst_umol_h, liquid_volume_L_h, AlTi_ratio, BHT_ratio, tau_h_total, p)
    act = activation_factor(AlTi_ratio, BHT_ratio, p)
    current_moles = inlet_moles.copy()
    segment_masses = {"E": 0.0, "P": 0.0, "D": 0.0}
    consumed_total = {name: 0.0 for name in MONOMERS}
    heat_total = 0.0
    stage_results: list[ReactorStage] = []
    rates_last = {"r_E": 0.0, "r_P": 0.0, "r_ENB": 0.0}
    for idx in range(1, stages_n + 1):
        concentrations = {
            "ethylene": current_moles["ethylene"] / liquid_volume_L_h,
            "propylene": current_moles["propylene"] / liquid_volume_L_h,
            "ENB": current_moles["ENB"] / liquid_volume_L_h,
        }
        rate = reaction_rates(concentrations, Cstar, temperature_K, pressure_MPa, p)
        kappa = {
            "ethylene": rate.k_E * Cstar,
            "propylene": rate.k_P * Cstar,
            "ENB": rate.k_ENB_eff * Cstar,
        }
        consumed: dict[str, float] = {}
        for monomer in MONOMERS:
            conv = _stage_conversion_factor(mode, kappa[monomer], tau_stage_h)
            consumed[monomer] = min(current_moles[monomer] * conv, current_moles[monomer])
            current_moles[monomer] -= consumed[monomer]
            consumed_total[monomer] += consumed[monomer]
        heat_stage = (
            consumed["ethylene"] * abs(p.dH_E_kJ_mol)
            + consumed["propylene"] * abs(p.dH_P_kJ_mol)
            + consumed["ENB"] * abs(p.dH_ENB_kJ_mol)
        )
        heat_total += heat_stage
        for monomer, mol in consumed.items():
            segment = SEGMENT_MAP[monomer]
            segment_masses[segment] += mol * components[monomer].MW / 1000.0
        polymer_stage = sum(consumed[m] * components[m].MW / 1000.0 for m in MONOMERS)
        rates_last = {
            "r_E": safe_divide(consumed["ethylene"], max(liquid_volume_L_h * tau_stage_h, TINY), 0.0),
            "r_P": safe_divide(consumed["propylene"], max(liquid_volume_L_h * tau_stage_h, TINY), 0.0),
            "r_ENB": safe_divide(consumed["ENB"], max(liquid_volume_L_h * tau_stage_h, TINY), 0.0),
        }
        stage_results.append(
            ReactorStage(
                stage=idx,
                tau_h=tau_stage_h,
                C_E_mol_L=concentrations["ethylene"],
                C_P_mol_L=concentrations["propylene"],
                C_ENB_mol_L=concentrations["ENB"],
                r_E_mol_L_h=rates_last["r_E"],
                r_P_mol_L_h=rates_last["r_P"],
                r_ENB_mol_L_h=rates_last["r_ENB"],
                ethylene_mol_h_out=current_moles["ethylene"],
                propylene_mol_h_out=current_moles["propylene"],
                ENB_mol_h_out=current_moles["ENB"],
                polymer_kg_h=sum(segment_masses.values()),
                heat_kJ_h=heat_total,
            )
        )
    for monomer in MONOMERS:
        outlet.molar_flows[monomer] = current_moles[monomer]
    outlet.sync_mass_from_moles(components)
    for key, value in inlet.mass_flows.items():
        if key not in MONOMERS:
            outlet.mass_flows[key] = value
    outlet.segment_masses_kg_h = segment_masses
    outlet.polymer_mass_kg_h = sum(segment_masses.values())
    outlet.update_solids()
    polymer_mass = outlet.polymer_mass_kg_h
    polymer_comp = {
        "ethylene_wt": 100.0 * safe_divide(segment_masses["E"], polymer_mass, 0.0),
        "propylene_wt": 100.0 * safe_divide(segment_masses["P"], polymer_mass, 0.0),
        "ENB_wt": 100.0 * safe_divide(segment_masses["D"], polymer_mass, 0.0),
    }
    conversions = {
        name: 100.0 * safe_divide(inlet_moles[name] - current_moles[name], inlet_moles[name], 0.0)
        for name in MONOMERS
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
