import numpy as np

from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.flowsheet import load_default_config
from epdm_sim.kinetics import KineticParameters
from epdm_sim.state_vector import build_state_layout_from_template, pack_state
from epdm_sim.template_ode_rhs import (
    build_template_ode_context,
    initial_template_ode_state,
    project_template_state,
    template_ode_rhs,
)
from epdm_sim.utils import c_to_k


def test_template_ode_rhs_returns_finite_derivative():
    cfg = load_default_config()
    layout = build_state_layout_from_template("EPDM_EPM_metallocene_solution")
    ctx = build_template_ode_context(
        "EPDM_EPM_metallocene_solution",
        layout,
        KineticParameters(),
        cfg,
        total_time_min=8.0,
    )
    state = initial_template_ode_state(
        ctx,
        solvent_mass_kg=cfg.solvent_mass_kg_h * 8.0 / 60.0,
        temperature_K=c_to_k(cfg.temperature_C),
        pressure_Pa=cfg.pressure_MPa * 1.0e6,
        catalyst_active_mol=cfg.catalyst_umol_h * 1.0e-6,
    )
    dy = template_ode_rhs(1.0, pack_state(layout, state), ctx)
    assert dy.shape == (len(layout.labels),)
    assert np.isfinite(dy).all()


def test_project_template_state_bounds_negative_entries():
    layout = build_state_layout_from_template("generic_terpolymerization_apparent")
    y = np.full(len(layout.labels), -1.0)
    projected = project_template_state(layout, y)
    assert np.isfinite(projected).all()
    assert projected.min() >= 0.0


def test_solve_ivp_path_uses_real_rhs_and_preserves_compatibility():
    cfg = load_default_config()
    result = simulate_template_semibatch_ode(
        "EPDM_EPM_metallocene_solution",
        config=cfg,
        total_time_min=6.0,
        dt_min=2.0,
        solver_mode="solve_ivp_rk45",
    )
    assert result.summary["solver_mode_used"] in {"solve_ivp_rk45", "explicit_bounded"}
    assert not result.profile.empty
    assert {"C_E", "C_P", "C_ENB"}.issubset(result.profile.columns)
    assert result.profile["polymer_mass_kg"].diff().dropna().ge(-1e-10).all()

