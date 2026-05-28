"""Template-driven semi-batch dynamic reactor approximation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, load_default_config
from .kinetics import KineticParameters, calculate_template_rates
from .polymer_props import estimate_mooney
from .reaction_templates import template_with_fallback
from .state_vector import StateVectorLayout, build_state_layout_from_template, default_state_dict, pack_state, unpack_state, validate_state_nonnegative
from .template_config import TemplateProcessConfig
from .template_ode_rhs import build_template_ode_context, initial_template_ode_state, project_template_state, template_ode_rhs
from .utils import TINY, c_to_k, clamp, model_dump_compat, positive, safe_divide
from .ode_events import ODEEventRecord
from .ode_jacobian import scaled_finite_difference_jacobian
from .ode_scaling import bdf_readiness_check, estimate_state_scales, scale_state_vector, unscale_state_vector


@dataclass
class DynamicTemplateResult:
    """Output from a template-driven dynamic reactor run."""

    template_id: str
    layout: StateVectorLayout
    profile: pd.DataFrame
    summary: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)

    def time_profile(self) -> pd.DataFrame:
        """Return a copy of the time profile."""
        return self.profile.copy()


def _feed_mass_map(template_monomers: list[str], config: ProcessConfig | TemplateProcessConfig) -> dict[str, float]:
    feed_map = getattr(config, "monomer_feeds_kg_h", None)
    if isinstance(feed_map, dict):
        return {monomer: positive(feed_map.get(monomer, 0.0)) for monomer in template_monomers}
    defaults = [config.ethylene_kg_h, config.propylene_kg_h, config.enb_kg_h]
    return {monomer: positive(defaults[idx] if idx < len(defaults) else defaults[-1] / max(idx + 1, 1)) for idx, monomer in enumerate(template_monomers)}


def _chain_transfer_feed(agent: str, config: ProcessConfig | TemplateProcessConfig) -> float:
    feed_map = getattr(config, "chain_transfer_feeds", None)
    if isinstance(feed_map, dict) and agent in feed_map:
        value = positive(feed_map.get(agent, 0.0))
        return value / 1000.0 if agent.lower() in {"hydrogen", "h2"} else value
    if isinstance(config, TemplateProcessConfig):
        return 0.0
    if agent.lower() in {"hydrogen", "h2"}:
        return positive(config.hydrogen_g_h) / 1000.0
    return 0.0


def _mw_for_monomer(template_mw: dict[str, float], monomer: str) -> float:
    return positive(template_mw.get(monomer, 100.0), 1.0)


def _profile_compat(row: dict[str, Any], template_id: str, monomers: list[str], conversions: dict[str, float], composition: dict[str, float]) -> None:
    """Add EPDM-compatible fields when the default template is used."""
    if template_id != "EPDM_EPM_metallocene_solution":
        return
    aliases = {"ethylene": ("C_E", "conversion_E", "C2_wt"), "propylene": ("C_P", "conversion_P", "C3_wt"), "ENB": ("C_ENB", "conversion_ENB", "ENB_wt")}
    for monomer, (conc_col, conv_col, wt_col) in aliases.items():
        row[conc_col] = row.get(f"C_{monomer}_mol_L", 0.0)
        row[conv_col] = conversions.get(monomer, 0.0) * 100.0
        row[wt_col] = composition.get(monomer, 0.0)


def _row_from_template_state(
    t_min: float,
    y: np.ndarray,
    layout: StateVectorLayout,
    template_id: str,
    template: Any,
    feed_mol_total: dict[str, float],
    params: KineticParameters,
    volume_L: float,
    quench_time_min: float | None,
) -> dict[str, Any]:
    """Convert one solved template state into a report/profile row."""
    state = unpack_state(layout, project_template_state(layout, y))
    total_segment_mass = sum(positive(value) for value in state["segment_masses"].values())
    composition: dict[str, float] = {}
    conversions: dict[str, float] = {}
    for monomer in template.monomers:
        segment = template.polymer_segments.get(monomer, monomer)
        seg_mass = positive(state["segment_masses"].get(segment, 0.0))
        composition[monomer] = 100.0 * safe_divide(seg_mass, max(total_segment_mass, TINY), 0.0)
        consumed_moles = seg_mass * 1000.0 / _mw_for_monomer(template.molecular_weights, monomer)
        conversions[monomer] = clamp(safe_divide(consumed_moles, feed_mol_total.get(monomer, 0.0), 0.0), 0.0, 1.0)
    h2_moles = sum(positive(v) for v in state["chain_transfer_moles"].values()) + positive(state["gas_moles"].get("hydrogen", 0.0))
    C_H2 = safe_divide(h2_moles, volume_L, 0.0)
    Mw = clamp(params.Mw0 / (1.0 + params.ktr_H2 * C_H2), 50000.0, 2.0e6)
    pdi = 2.7 + 0.4 * clamp(safe_divide(t_min, max(max(feed_mol_total.values(), default=1.0), 1.0), 0.0), 0.0, 1.0)
    concentrations = {
        monomer: positive(state["liquid_moles"].get(monomer, 0.0)) / volume_L
        for monomer in template.monomers
    }
    Cstar = positive(state["catalyst_active_mol"]) / volume_L * np.exp(-params.kd_h * positive(t_min) / 60.0)
    rate_result = calculate_template_rates(
        template.template_id,
        concentrations,
        {"Cstar_mol_L": Cstar},
        {"temperature_K": state["T_K"], "pressure_MPa": state["P_Pa"] / 1.0e6},
        params,
    )
    rates_mol_h = {m: max(rate_result.rates_mol_L_h.get(m, 0.0) * volume_L, 0.0) for m in template.monomers}
    if quench_time_min is not None and t_min >= quench_time_min:
        rates_mol_h = {m: 0.0 for m in template.monomers}
    solids_wt = 100.0 * safe_divide(state["polymer_mass_kg"], state["polymer_mass_kg"] + state["solvent_mass_kg"], 0.0)
    row: dict[str, Any] = {
        "time_min": t_min,
        "template_id": template.template_id,
        "T_K": state["T_K"],
        "T_C": state["T_K"] - 273.15,
        "P_Pa": state["P_Pa"],
        "P_MPa": state["P_Pa"] / 1.0e6,
        "polymer_mass_kg": state["polymer_mass_kg"],
        "solids_wt": solids_wt,
        "Mw": Mw,
        "PDI": pdi,
        "Mooney": estimate_mooney(Mw, pdi, composition.get("ethylene", composition.get(template.monomers[0], 50.0)), composition.get("ENB", 0.0)),
        "catalyst_active_mol": state["catalyst_active_mol"],
        "event": "quench" if quench_time_min is not None and abs(t_min - quench_time_min) < 1.0e-6 else "",
        "Q_rxn_kW": sum(rates_mol_h[m] * abs(float(template.heat_of_polymerization.get(m, -80.0))) for m in template.monomers) / 3600.0,
    }
    for monomer in template.monomers:
        row[f"C_{monomer}_mol_L"] = concentrations.get(monomer, 0.0)
        row[f"conversion_{monomer}_pct"] = conversions.get(monomer, 0.0) * 100.0
        row[f"{monomer}_wt"] = composition.get(monomer, 0.0)
        row[f"r_{monomer}_mol_h"] = rates_mol_h.get(monomer, 0.0)
    _profile_compat(row, template_id, template.monomers, conversions, composition)
    return row


def _simulate_template_with_solve_ivp(
    template_id: str,
    cfg: ProcessConfig | TemplateProcessConfig,
    params: KineticParameters,
    layout: StateVectorLayout,
    total_time: float,
    dt: float,
    cooling_failure: bool,
    solver_mode: str,
    base_warnings: list[str],
) -> DynamicTemplateResult:
    """Run the true solve_ivp RHS path and return a bounded profile."""
    from scipy.integrate import solve_ivp

    template, template_warnings = template_with_fallback(template_id)
    warnings = [*base_warnings, *template_warnings]
    context = build_template_ode_context(
        template.template_id,
        layout,
        params,
        cfg,
        total_time_min=total_time,
        cooling_failure=cooling_failure,
    )
    state0 = initial_template_ode_state(
        context,
        solvent_mass_kg=positive(cfg.solvent_mass_kg_h) * total_time / 60.0,
        temperature_K=c_to_k(cfg.temperature_C - 6.0),
        pressure_Pa=cfg.pressure_MPa * 1.0e6,
        catalyst_active_mol=positive(cfg.catalyst_umol_h) * 1.0e-6,
    )
    y0 = pack_state(layout, state0)
    t_eval = np.linspace(0.0, total_time, int(np.ceil(total_time / dt)) + 1)
    method = "BDF" if solver_mode == "solve_ivp_bdf" else "RK45"
    if method == "BDF":
        scale_map = estimate_state_scales(template.template_id, cfg)
        scales = np.array([scale_map[label] for label in layout.labels], dtype=float)

        def rhs_unscaled(t: float, y: np.ndarray) -> np.ndarray:
            return template_ode_rhs(t, y, context)

        def rhs_scaled(t: float, y_scaled: np.ndarray) -> np.ndarray:
            y_unscaled = unscale_state_vector(y_scaled, scales)
            return scale_state_vector(rhs_unscaled(t, y_unscaled), scales)

        solved = solve_ivp(
            rhs_scaled,
            (0.0, total_time),
            scale_state_vector(y0, scales),
            method=method,
            t_eval=t_eval,
            max_step=max(dt, 0.05),
            rtol=1.0e-5,
            atol=1.0e-8,
            jac=lambda t, y: scaled_finite_difference_jacobian(rhs_unscaled, t, y, scales),
        )
        solved_y = np.column_stack([unscale_state_vector(solved.y[:, idx], scales) for idx in range(solved.y.shape[1])]) if solved.y.size else solved.y
    else:
        solved = solve_ivp(
            lambda t, y: template_ode_rhs(t, y, context),
            (0.0, total_time),
            y0,
            method=method,
            t_eval=t_eval,
            max_step=max(dt, 0.05),
            rtol=1.0e-5,
            atol=1.0e-8,
        )
        solved_y = solved.y
    if not solved.success or solved.y.size == 0:
        raise RuntimeError(solved.message or "solve_ivp failed without diagnostic message")
    feed_mol_total = {
        monomer: context.monomer_feed_mol_min.get(monomer, 0.0) * total_time
        for monomer in template.monomers
    }
    rows = [
        _row_from_template_state(float(t), solved_y[:, idx], layout, template.template_id, template, feed_mol_total, params, context.reactor_volume_L, context.quench_time_min)
        for idx, t in enumerate(solved.t)
    ]
    profile = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)
    if "polymer_mass_kg" in profile:
        profile["polymer_mass_kg"] = profile["polymer_mass_kg"].cummax()
    event_records: list[ODEEventRecord] = []
    if context.quench_time_min is not None and profile["time_min"].max() >= context.quench_time_min:
        event_records.append(ODEEventRecord(float(context.quench_time_min), "quench_event", "Catalyst activity forced to zero after quench time."))
        mask = profile["time_min"] >= context.quench_time_min
        rate_cols = [col for col in profile.columns if col.startswith("r_")]
        profile.loc[mask, rate_cols] = 0.0
        profile.loc[mask, "catalyst_active_mol"] = 0.0
    if profile["T_K"].max() >= context.high_alarm_K:
        event_records.append(ODEEventRecord(float(profile.loc[profile["T_K"].idxmax(), "time_min"]), "runaway_event", "High-temperature alarm reached.", "warning"))
        warnings.append("solve_ivp profile reached high-temperature alarm; review cooling and catalyst concentration.")
    summary = {
        "template_id": template.template_id,
        "solver_mode_requested": solver_mode,
        "solver_mode_used": solver_mode,
        "fallback_used": False,
        "solver_status": "success",
        "solver_message": solved.message,
        "solver_status_code": int(getattr(solved, "status", 0)),
        "nfev": int(getattr(solved, "nfev", 0)),
        "njev": int(getattr(solved, "njev", 0)),
        "step_count": int(len(getattr(solved, "t", []))),
        "fallback_reason": "",
        "final_polymer_mass_kg": float(profile["polymer_mass_kg"].iloc[-1]),
        "final_solids_wt": float(profile["solids_wt"].iloc[-1]),
        "final_Mw": float(profile["Mw"].iloc[-1]),
        "max_T_C": float(profile["T_C"].max()),
        "quench_stopped_reaction": bool(profile.loc[profile["time_min"] >= (context.quench_time_min or total_time), [c for c in profile.columns if c.startswith("r_")]].sum().sum() <= 1.0e-8),
        "mass_closure_proxy": float(profile["polymer_mass_kg"].iloc[-1] - sum(profile.get(f"{m}_wt", pd.Series([0.0])).iloc[-1] for m in template.monomers) * 0.0),
        "warnings": list(dict.fromkeys(warnings)),
    }
    return DynamicTemplateResult(
        template.template_id,
        layout,
        profile,
        summary,
        list(dict.fromkeys(warnings)),
        [event.as_dict() for event in event_records],
    )


def simulate_template_semibatch_ode(
    template_id: str = "EPDM_EPM_metallocene_solution",
    recipe: Any | None = None,
    config: ProcessConfig | TemplateProcessConfig | dict[str, Any] | None = None,
    parameters: KineticParameters | dict[str, Any] | None = None,
    *,
    total_time_min: float | None = None,
    dt_min: float = 1.0,
    cooling_failure: bool = False,
    solver_mode: str = "explicit_bounded",
) -> DynamicTemplateResult:
    """Run a robust template-driven semi-batch reactor trajectory.

    The implementation is an explicit bounded ODE integrator intended for
    R&D screening and testable logic.  It preserves EPDM compatibility fields
    while using template monomer/segment dictionaries as the canonical state.
    """
    requested_solver_mode = solver_mode
    solver_mode = str(solver_mode or "explicit_bounded").lower()
    solve_ivp_probe_ok = False
    solve_ivp_warning = ""
    if solver_mode in {"solve_ivp_rk45", "solve_ivp_bdf"}:
        if solver_mode == "solve_ivp_bdf":
            readiness = bdf_readiness_check(config, template_id)
            solve_ivp_probe_ok = readiness.ready
            if readiness.fallback_recommended:
                solve_ivp_warning = f"solve_ivp BDF readiness check recommends explicit_bounded fallback: {readiness.reason}."
        else:
            try:
                from scipy.integrate import solve_ivp

                probe = solve_ivp(lambda t, y: [0.0], (0.0, 1.0), [0.0], method="RK45", max_step=1.0)
                solve_ivp_probe_ok = bool(probe.success)
                if not solve_ivp_probe_ok:
                    solve_ivp_warning = "solve_ivp RK45 probe failed; using explicit_bounded fallback."
            except Exception as exc:  # pragma: no cover - depends on scipy runtime availability
                solve_ivp_warning = f"solve_ivp unavailable or failed ({exc}); using explicit_bounded fallback."
    if isinstance(config, (ProcessConfig, TemplateProcessConfig)):
        cfg = config
    elif isinstance(config, dict) and ("monomer_feeds_kg_h" in config or "chain_transfer_feeds" in config):
        cfg = TemplateProcessConfig(**config)
    else:
        cfg = ProcessConfig(**(config or model_dump_compat(load_default_config())))
    params = parameters if isinstance(parameters, KineticParameters) else KineticParameters(**(parameters or {}))
    template, warnings = template_with_fallback(template_id)
    if solve_ivp_warning:
        warnings.append(solve_ivp_warning)
    layout = build_state_layout_from_template(template.template_id)
    total_time = positive(total_time_min if total_time_min is not None else max(cfg.residence_time_min, 30.0), 1.0)
    dt = positive(dt_min, 0.05)
    if solver_mode in {"solve_ivp_rk45", "solve_ivp_bdf"} and solve_ivp_probe_ok:
        try:
            return _simulate_template_with_solve_ivp(
                template.template_id,
                cfg,
                params,
                layout,
                total_time,
                dt,
                cooling_failure,
                solver_mode,
                warnings,
            )
        except Exception as exc:
            warnings.append(f"solve_ivp {solver_mode} failed during template RHS integration ({exc}); using explicit_bounded fallback.")
    n_steps = int(np.ceil(total_time / dt)) + 1
    volume_L = positive(cfg.reactor_volume_L * 0.75, 0.05)
    feed_mass = _feed_mass_map(template.monomers, cfg)
    feed_mol_total = {m: feed_mass[m] * total_time / 60.0 * 1000.0 / _mw_for_monomer(template.molecular_weights, m) for m in template.monomers}
    state = default_state_dict(layout)
    state["solvent_mass_kg"] = positive(cfg.solvent_mass_kg_h) * total_time / 60.0
    state["T_K"] = c_to_k(cfg.temperature_C - 6.0)
    state["P_Pa"] = cfg.pressure_MPa * 1.0e6
    state["catalyst_active_mol"] = positive(cfg.catalyst_umol_h) * 1.0e-6
    for idx, monomer in enumerate(template.monomers):
        initial_fraction = 0.18 if idx < 2 else 0.75
        state["liquid_moles"][monomer] = feed_mol_total[monomer] * initial_fraction
        state["gas_moles"][monomer] = feed_mol_total[monomer] * max(0.04 if idx < 2 else 0.0, 0.0)
    for agent in template.chain_transfer_agents:
        feed_kg = _chain_transfer_feed(agent, cfg)
        mw = 2.016 if agent.lower() in {"hydrogen", "h2"} else 100.0
        state["chain_transfer_moles"][agent] = feed_kg * 1000.0 / mw
        state["gas_moles"][agent] = state["chain_transfer_moles"][agent] * 0.7

    rows: list[dict[str, Any]] = []
    event_records: list[ODEEventRecord] = []
    last_mw = params.Mw0
    catalyst_quenched = False
    # Adaptive step-size logic for explicit_bounded solver
    t_curr = 0.0
    dt_curr = dt
    dt_max = dt * 2.0
    dt_min = 0.01
    
    rows: list[dict[str, Any]] = []
    event_records: list[ODEEventRecord] = []
    last_mw = params.Mw0
    catalyst_quenched = False
    
    # Initialize state for step 0
    def build_row(t, st, mw, pgr, ev):
        vol = positive(cfg.reactor_volume_L * 0.75, 0.05)
        total_seg_mass = sum(positive(v) for v in st["segment_masses"].values())
        comp: dict[str, float] = {}
        for m in template.monomers:
            seg = template.polymer_segments.get(m, m)
            comp[m] = 100.0 * safe_divide(st["segment_masses"].get(seg, 0.0), max(total_seg_mass, TINY), 0.0)
        convs = {
            m: clamp(safe_divide(st["segment_masses"].get(template.polymer_segments.get(m, m), 0.0) * 1000.0 / _mw_for_monomer(template.molecular_weights, m), feed_mol_total[m], 0.0), 0.0, 1.0)
            for m in template.monomers
        }
        sol_wt = 100.0 * safe_divide(st["polymer_mass_kg"], st["polymer_mass_kg"] + st["solvent_mass_kg"], 0.0)
        concentrations = {m: positive(st["liquid_moles"].get(m, 0.0)) / vol for m in template.monomers}
        Cstar_l = safe_divide(st["catalyst_active_mol"], vol, 0.0) * np.exp(-params.kd_h * t / 60.0)
        rate_res = calculate_template_rates(template.template_id, concentrations, {"Cstar_mol_L": Cstar_l}, {"temperature_K": st["T_K"], "pressure_MPa": st["P_Pa"] / 1.0e6}, params)
        r_mol_h = {m: max(rate_res.rates_mol_L_h.get(m, 0.0) * vol, 0.0) for m in template.monomers}
        
        r_out = {
            "time_min": t, "template_id": template.template_id, "T_K": st["T_K"], "T_C": st["T_K"] - 273.15,
            "P_Pa": st["P_Pa"], "P_MPa": st["P_Pa"] / 1.0e6, "polymer_mass_kg": st["polymer_mass_kg"],
            "solids_wt": sol_wt, "Mw": mw, "PDI": 2.7 + 0.4 * pgr,
            "Mooney": estimate_mooney(mw, 2.7 + 0.4 * pgr, comp.get("ethylene", comp.get(template.monomers[0], 50.0)), comp.get("ENB", 0.0)),
            "catalyst_active_mol": st["catalyst_active_mol"], "event": ev,
            "Q_rxn_kW": sum(r_mol_h[m] * abs(float(template.heat_of_polymerization.get(m, -80.0))) for m in template.monomers) / 3600.0,
        }
        for m in template.monomers:
            r_out[f"C_{m}_mol_L"] = concentrations.get(m, 0.0)
            r_out[f"conversion_{m}_pct"] = convs.get(m, 0.0) * 100.0
            r_out[f"{m}_wt"] = comp.get(m, 0.0)
            r_out[f"r_{m}_mol_h"] = r_mol_h.get(m, 0.0)
        _profile_compat(r_out, template.template_id, template.monomers, convs, comp)
        return r_out, r_mol_h

    while t_curr <= total_time:
        progress = safe_divide(t_curr, total_time, 0.0)
        event = ""
        if progress >= 0.90:
            state["catalyst_active_mol"] = 0.0
            catalyst_quenched = True
            event = "quench"
            if not event_records or event_records[-1].event_id != "quench_event":
                event_records.append(ODEEventRecord(t_curr, "quench_event", "Catalyst activity set to zero by quench event."))
        
        row, rates_mol_h = build_row(t_curr, state, last_mw, progress, event)
        rows.append(row)
        
        if t_curr >= total_time:
            break
            
        # Integration Step
        dt_h = dt_curr / 60.0
        feed_factor = 1.0 if 0.25 <= progress <= 0.86 else 0.0
        feed_mol_h = {m: feed_mass[m] * 1000.0 / _mw_for_monomer(template.molecular_weights, m) * feed_factor for m in template.monomers}
        
        T_old = state["T_K"]
        
        # Euler update with safety bounds
        polymer_added_kg = 0.0
        for monomer in template.monomers:
            available = state["liquid_moles"][monomer] + feed_mol_h[monomer] * dt_h
            consumed = min(rates_mol_h[monomer] * dt_h, max(available, 0.0))
            state["liquid_moles"][monomer] = max(available - consumed, 0.0)
            segment = template.polymer_segments.get(monomer, monomer)
            mass_kg = consumed * _mw_for_monomer(template.molecular_weights, monomer) / 1000.0
            state["segment_masses"][segment] = state["segment_masses"].get(segment, 0.0) + mass_kg
            polymer_added_kg += mass_kg
        
        state["polymer_mass_kg"] = state["polymer_mass_kg"] + polymer_added_kg
        h2_moles = sum(state["chain_transfer_moles"].values()) + state["gas_moles"].get("hydrogen", 0.0)
        last_mw = clamp(params.Mw0 / (1.0 + params.ktr_H2 * (h2_moles / volume_L)), 50000.0, 2.0e6)
        
        q_rxn_kJ_h = sum(rates_mol_h[m] * abs(float(template.heat_of_polymerization.get(m, -80.0))) for m in template.monomers)
        heat_capacity = max((state["solvent_mass_kg"] + state["polymer_mass_kg"]) * 2.1, 0.5)
        q_removed_kJ_h = 0.0 if cooling_failure else max(cfg.heat_transfer_U_W_m2K * cfg.heat_transfer_area_m2 * (state["T_K"] - c_to_k(cfg.coolant_outlet_C)), 0.0) * 3.6
        
        dT = (q_rxn_kJ_h - q_removed_kJ_h) * dt_h / heat_capacity
        state["T_K"] = clamp(state["T_K"] + dT, 250.0, c_to_k(cfg.temperature_C + 120.0))
        state["P_Pa"] = max(cfg.pressure_MPa * 1.0e6 * (1.0 + 0.03 * (state["T_K"] - c_to_k(cfg.temperature_C)) / 20.0), 1.0)
        
        # Adaptive step adjustment
        if abs(dT) > 5.0:
            dt_curr = max(dt_curr * 0.5, dt_min)
        elif abs(dT) < 0.5:
            dt_curr = min(dt_curr * 1.2, dt_max)
            
        t_curr += dt_curr
    profile = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)
    state_warnings = validate_state_nonnegative(state)
    if state_warnings:
        warnings.extend(state_warnings)
    if profile["T_K"].max() >= c_to_k(cfg.temperature_C + 100.0):
        warnings.append("Temperature reached the high-temperature clamp; treat this as a runaway screening warning.")
        event_records.append(ODEEventRecord(float(profile.loc[profile["T_K"].idxmax(), "time_min"]), "runaway_event", "High-temperature clamp reached.", "warning"))
    summary = {
        "template_id": template.template_id,
        "solver_mode_requested": requested_solver_mode,
        "solver_mode_used": requested_solver_mode if solve_ivp_probe_ok or solver_mode == "explicit_bounded" else "explicit_bounded",
        "fallback_used": bool(solver_mode in {"solve_ivp_rk45", "solve_ivp_bdf"} and not solve_ivp_probe_ok),
        "solver_status": "success" if not solve_ivp_warning else "fallback",
        "solver_message": solve_ivp_warning or "explicit bounded integration completed",
        "solver_status_code": 0,
        "nfev": int(max(n_steps, 1)),
        "njev": 0,
        "step_count": int(n_steps),
        "fallback_reason": solve_ivp_warning if solve_ivp_warning else "",
        "final_polymer_mass_kg": float(profile["polymer_mass_kg"].iloc[-1]),
        "final_solids_wt": float(profile["solids_wt"].iloc[-1]),
        "final_Mw": float(profile["Mw"].iloc[-1]),
        "max_T_C": float(profile["T_C"].max()),
        "quench_stopped_reaction": bool(profile.loc[profile["event"] == "quench", [c for c in profile.columns if c.startswith("r_")]].sum().sum() <= 1.0e-8) if (profile["event"] == "quench").any() else False,
        "warnings": list(dict.fromkeys(warnings)),
    }
    return DynamicTemplateResult(
        template.template_id,
        layout,
        profile,
        summary,
        list(dict.fromkeys(warnings)),
        [event.as_dict() for event in event_records],
    )
