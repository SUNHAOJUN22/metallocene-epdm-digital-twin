"""Template-native ODE right-hand side for dynamic polymerization reactors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import math
import numpy as np

from .dimensioned import ensure_pressure_Pa, ensure_temperature_K, ensure_time_min
from .kinetics import KineticParameters, calculate_template_rates
from .reaction_templates import ReactionTemplate, template_with_fallback
from .state_vector import StateVectorLayout, pack_state, unpack_state
from .utils import TINY, c_to_k, clamp, positive, safe_divide


@dataclass(frozen=True)
class TemplateODERHSContext:
    """Inputs needed by the template ODE RHS.

    The independent variable is minutes.  Extensive derivatives are returned
    per minute, while reaction rates from the kinetics module are converted
    from mol/L/h to mol/min.
    """

    template: ReactionTemplate
    layout: StateVectorLayout
    parameters: KineticParameters
    monomer_feed_mol_min: dict[str, float]
    chain_transfer_feed_mol_min: dict[str, float]
    reactor_volume_L: float
    pressure_setpoint_Pa: float
    coolant_temperature_K: float
    overall_UA_W_K: float
    cooling_enabled: bool = True
    quench_time_min: float | None = None
    high_alarm_K: float = 453.15
    feed_start_fraction: float = 0.20
    feed_end_fraction: float = 0.88
    total_time_min: float = 30.0
    warnings: list[str] = field(default_factory=list)


def build_template_ode_context(
    template_id: str,
    layout: StateVectorLayout,
    parameters: KineticParameters,
    config: Any,
    *,
    total_time_min: float,
    cooling_failure: bool = False,
) -> TemplateODERHSContext:
    """Build a physically bounded RHS context from a process-like config."""
    template, warnings = template_with_fallback(template_id)
    total_time = ensure_time_min(total_time_min, default_unit="min")
    monomer_feed_mol_min: dict[str, float] = {}
    feed_map = getattr(config, "monomer_feeds_kg_h", None)
    if isinstance(feed_map, dict):
        for monomer in template.monomers:
            kg_h = positive(feed_map.get(monomer, 0.0))
            mw = positive(template.molecular_weights.get(monomer, 100.0), 1.0)
            monomer_feed_mol_min[monomer] = kg_h * 1000.0 / mw / 60.0
    else:
        aliases = {
            "ethylene": positive(getattr(config, "ethylene_kg_h", 0.0)),
            "propylene": positive(getattr(config, "propylene_kg_h", 0.0)),
            "ENB": positive(getattr(config, "enb_kg_h", 0.0)),
        }
        fallback = list(aliases.values()) or [0.0]
        for idx, monomer in enumerate(template.monomers):
            kg_h = positive(aliases.get(monomer, fallback[min(idx, len(fallback) - 1)]))
            mw = positive(template.molecular_weights.get(monomer, 100.0), 1.0)
            monomer_feed_mol_min[monomer] = kg_h * 1000.0 / mw / 60.0
    chain_transfer_feed_mol_min: dict[str, float] = {}
    cta_map = getattr(config, "chain_transfer_feeds", None)
    for agent in template.chain_transfer_agents:
        if isinstance(cta_map, dict):
            mass_value = positive(cta_map.get(agent, 0.0))
            kg_h = mass_value / 1000.0 if agent.lower() in {"h2", "hydrogen"} else mass_value
        elif agent.lower() in {"h2", "hydrogen"}:
            kg_h = positive(getattr(config, "hydrogen_g_h", 0.0)) / 1000.0
        else:
            kg_h = 0.0
        mw = 2.016 if agent.lower() in {"h2", "hydrogen"} else 100.0
        chain_transfer_feed_mol_min[agent] = kg_h * 1000.0 / mw / 60.0
    return TemplateODERHSContext(
        template=template,
        layout=layout,
        parameters=parameters,
        monomer_feed_mol_min=monomer_feed_mol_min,
        chain_transfer_feed_mol_min=chain_transfer_feed_mol_min,
        reactor_volume_L=positive(getattr(config, "reactor_volume_L", 5.0) * 0.75, 0.05),
        pressure_setpoint_Pa=ensure_pressure_Pa((getattr(config, "pressure_MPa", 1.0), "MPa")),
        coolant_temperature_K=ensure_temperature_K((getattr(config, "coolant_outlet_C", getattr(config, "coolant_temperature_C", 35.0)), "°C")),
        overall_UA_W_K=positive(getattr(config, "heat_transfer_U_W_m2K", 300.0) * getattr(config, "heat_transfer_area_m2", 2.0)),
        cooling_enabled=not cooling_failure,
        quench_time_min=0.90 * total_time,
        high_alarm_K=c_to_k(getattr(config, "temperature_C", 100.0) + 70.0),
        total_time_min=total_time,
        warnings=warnings,
    )


def initial_template_ode_state(
    context: TemplateODERHSContext,
    *,
    solvent_mass_kg: float,
    temperature_K: float,
    pressure_Pa: float,
    catalyst_active_mol: float,
) -> dict[str, Any]:
    """Create a non-negative initial state for template ODE integration."""
    state = {
        "liquid_moles": {name: 0.0 for name in context.layout.liquid_moles},
        "gas_moles": {name: 0.0 for name in context.layout.gas_moles},
        "segment_masses": {name: 0.0 for name in context.layout.segment_masses},
        "chain_transfer_moles": {name: 0.0 for name in context.layout.chain_transfer_moles},
        "solvent_mass_kg": positive(solvent_mass_kg),
        "polymer_mass_kg": 0.0,
        "T_K": ensure_temperature_K(temperature_K, default_unit="K"),
        "P_Pa": ensure_pressure_Pa(pressure_Pa, default_unit="Pa"),
        "catalyst_active_mol": positive(catalyst_active_mol),
        "time_min": 0.0,
    }
    startup_inventory_min = max(0.18 * context.total_time_min, 1.0)
    for monomer in context.template.monomers:
        fed = context.monomer_feed_mol_min.get(monomer, 0.0) * startup_inventory_min
        state["liquid_moles"][monomer] = 0.75 * fed
        if monomer in state["gas_moles"]:
            state["gas_moles"][monomer] = 0.25 * fed
    for agent in context.template.chain_transfer_agents:
        fed = context.chain_transfer_feed_mol_min.get(agent, 0.0) * startup_inventory_min
        state["chain_transfer_moles"][agent] = 0.35 * fed
        if agent in state["gas_moles"]:
            state["gas_moles"][agent] = 0.65 * fed
    return state


def template_ode_rhs(t_min: float, y: np.ndarray, context: TemplateODERHSContext) -> np.ndarray:
    """Return dy/dt for a template semi-batch polymerization reactor."""
    state = unpack_state(context.layout, y)
    for group in ("liquid_moles", "gas_moles", "segment_masses", "chain_transfer_moles"):
        state[group] = {key: positive(value) for key, value in state.get(group, {}).items()}
    state["T_K"] = positive(state.get("T_K", 373.15), 1.0)
    state["P_Pa"] = positive(state.get("P_Pa", context.pressure_setpoint_Pa), 1.0)
    state["catalyst_active_mol"] = positive(state.get("catalyst_active_mol", 0.0))
    progress = clamp(safe_divide(float(t_min), positive(context.total_time_min, 1.0), 0.0), 0.0, 1.0)
    # Smoothly transition feed window and pressure-deficit factor using sigmoid/tanh
    # to maintain RHS differentiability for the stiff BDF solver.
    def smooth_step(x: float, threshold: float, width: float = 0.01) -> float:
        return 0.5 * (1.0 + math.tanh((x - threshold) / width))

    window_low = smooth_step(progress, context.feed_start_fraction, 0.005)
    window_high = 1.0 - smooth_step(progress, context.feed_end_fraction, 0.005)
    feed_window_smooth = window_low * window_high
    
    p_err = (context.pressure_setpoint_Pa - state["P_Pa"]) / context.pressure_setpoint_Pa
    pressure_feed_factor = 0.5 * (1.0 + math.tanh(p_err / 0.005))
    feed_factor = feed_window_smooth * pressure_feed_factor
    catalyst_active = state["catalyst_active_mol"]
    if context.quench_time_min is not None and t_min >= context.quench_time_min:
        catalyst_active = 0.0
    volume_L = positive(context.reactor_volume_L, 0.05)
    concentrations = {
        monomer: positive(state["liquid_moles"].get(monomer, 0.0)) / volume_L
        for monomer in context.template.monomers
    }
    Cstar = catalyst_active / volume_L * np.exp(-context.parameters.kd_h * positive(t_min) / 60.0)
    rates = calculate_template_rates(
        context.template.template_id,
        concentrations,
        {"Cstar_mol_L": Cstar},
        {"temperature_K": state["T_K"], "pressure_MPa": state["P_Pa"] / 1.0e6},
        context.parameters,
    )
    reaction_mol_min = {
        monomer: max(rates.rates_mol_L_h.get(monomer, 0.0) * volume_L / 60.0, 0.0)
        for monomer in context.template.monomers
    }
    # Smooth substrate limiting keeps the RHS continuous near zero inventory.
    for monomer, value in list(reaction_mol_min.items()):
        inventory = positive(state["liquid_moles"].get(monomer, 0.0))
        reaction_mol_min[monomer] = value * safe_divide(inventory, inventory + 1.0e-6, 0.0)
    d_state = {
        "liquid_moles": {name: 0.0 for name in context.layout.liquid_moles},
        "gas_moles": {name: 0.0 for name in context.layout.gas_moles},
        "segment_masses": {name: 0.0 for name in context.layout.segment_masses},
        "chain_transfer_moles": {name: 0.0 for name in context.layout.chain_transfer_moles},
        "solvent_mass_kg": 0.0,
        "polymer_mass_kg": 0.0,
        "T_K": 0.0,
        "P_Pa": 0.0,
        "catalyst_active_mol": 0.0,
        "time_min": 1.0,
    }
    q_rxn_kJ_min = 0.0
    for monomer in context.template.monomers:
        feed = context.monomer_feed_mol_min.get(monomer, 0.0) * feed_factor
        gas = positive(state["gas_moles"].get(monomer, 0.0))
        liquid = positive(state["liquid_moles"].get(monomer, 0.0))
        kLa_min = 0.10 if monomer in {"ethylene", "propylene"} or monomer.startswith("monomer_") else 0.02
        transfer = kLa_min * (0.18 * gas - 0.02 * liquid)
        reacted = reaction_mol_min[monomer]
        d_state["liquid_moles"][monomer] = feed + transfer - reacted
        if monomer in d_state["gas_moles"]:
            d_state["gas_moles"][monomer] = 0.15 * feed - transfer
        segment = context.template.polymer_segments.get(monomer, monomer)
        mass_kg_min = reacted * positive(context.template.molecular_weights.get(monomer, 100.0), 1.0) / 1000.0
        d_state["segment_masses"][segment] = d_state["segment_masses"].get(segment, 0.0) + mass_kg_min
        d_state["polymer_mass_kg"] += mass_kg_min
        q_rxn_kJ_min += reacted * abs(float(context.template.heat_of_polymerization.get(monomer, -80.0)))
    for agent in context.template.chain_transfer_agents:
        feed = context.chain_transfer_feed_mol_min.get(agent, 0.0) * feed_factor
        gas = positive(state["gas_moles"].get(agent, 0.0))
        liquid = positive(state["chain_transfer_moles"].get(agent, 0.0))
        transfer = 0.12 * (0.20 * gas - 0.03 * liquid)
        d_state["chain_transfer_moles"][agent] = feed + transfer
        if agent in d_state["gas_moles"]:
            d_state["gas_moles"][agent] = 0.30 * feed - transfer
    if context.quench_time_min is not None and t_min >= context.quench_time_min:
        d_state["catalyst_active_mol"] = -50.0 * state["catalyst_active_mol"]
    else:
        d_state["catalyst_active_mol"] = -context.parameters.kd_h / 60.0 * state["catalyst_active_mol"]
    total_mass_kg = positive(state.get("solvent_mass_kg", 0.0) + state.get("polymer_mass_kg", 0.0), 0.2)
    heat_capacity_kJ_K = max(total_mass_kg * 2.1, 0.1)
    q_removed_kJ_min = 0.0
    if context.cooling_enabled:
        q_removed_kJ_min = max(context.overall_UA_W_K * (state["T_K"] - context.coolant_temperature_K), 0.0) * 0.060
    d_state["T_K"] = (q_rxn_kJ_min - q_removed_kJ_min) / heat_capacity_kJ_K
    gas_total = sum(positive(value) for value in state.get("gas_moles", {}).values())
    d_gas_total = sum(d_state["gas_moles"].values())
    d_state["P_Pa"] = context.pressure_setpoint_Pa * 0.015 * safe_divide(d_gas_total, max(gas_total, 1.0), 0.0)
    # Avoid driving pressure below vacuum in long integrations.
    if state["P_Pa"] < 0.2 * context.pressure_setpoint_Pa and d_state["P_Pa"] < 0.0:
        d_state["P_Pa"] = 0.0
    if state["T_K"] >= context.high_alarm_K and d_state["T_K"] > 0.0:
        d_state["T_K"] *= 0.25
    return pack_state(context.layout, d_state)


def project_template_state(layout: StateVectorLayout, y: np.ndarray) -> np.ndarray:
    """Project a flat state vector onto finite physical bounds."""
    state = unpack_state(layout, y)
    for group in ("liquid_moles", "gas_moles", "segment_masses", "chain_transfer_moles"):
        state[group] = {key: positive(value) for key, value in state.get(group, {}).items()}
    state["solvent_mass_kg"] = positive(state.get("solvent_mass_kg", 0.0))
    state["polymer_mass_kg"] = positive(state.get("polymer_mass_kg", 0.0))
    state["T_K"] = clamp(positive(state.get("T_K", 373.15), 1.0), 200.0, 650.0)
    state["P_Pa"] = positive(state.get("P_Pa", 1.0e6), 1.0)
    state["catalyst_active_mol"] = positive(state.get("catalyst_active_mol", 0.0))
    state["time_min"] = positive(state.get("time_min", 0.0))
    return pack_state(layout, state)
