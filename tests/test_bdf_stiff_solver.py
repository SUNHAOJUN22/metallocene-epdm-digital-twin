import math

import numpy as np

from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.ode_jacobian import finite_difference_jacobian, jacobian_diagnostic
from epdm_sim.ode_scaling import bdf_readiness_check


def test_bdf_stiff_solver_runs_or_engineered_fallback():
    result = simulate_template_semibatch_ode(
        total_time_min=3.0,
        dt_min=1.0,
        solver_mode="solve_ivp_bdf",
    )
    assert not result.profile.empty
    assert result.summary["solver_mode_requested"] == "solve_ivp_bdf"
    assert result.summary["nfev"] > 0
    assert result.summary["step_count"] > 0
    assert "fallback_reason" in result.summary
    assert np.isfinite(result.profile[["T_K", "P_Pa", "polymer_mass_kg"]].to_numpy()).all()
    assert (result.profile["P_Pa"] > 0).all()
    assert (result.profile["polymer_mass_kg"].diff().fillna(0.0) >= -1e-12).all()
    conversion_cols = [col for col in result.profile.columns if col.startswith("conversion_") and col.endswith("_pct")]
    for col in conversion_cols:
        assert result.profile[col].between(0.0, 100.0).all()


def test_bdf_quench_stops_reaction_rates():
    result = simulate_template_semibatch_ode(
        total_time_min=5.0,
        dt_min=1.0,
        solver_mode="solve_ivp_bdf",
    )
    rate_cols = [col for col in result.profile.columns if col.startswith("r_")]
    quenched = result.profile[result.profile["time_min"] >= 0.9 * 5.0]
    assert not quenched.empty
    assert float(quenched[rate_cols].abs().sum().sum()) <= 1e-8
    assert result.summary["quench_stopped_reaction"] is True


def test_bdf_readiness_and_jacobian_are_finite():
    readiness = bdf_readiness_check(template_id="EPDM_EPM_metallocene_solution")
    assert math.isfinite(readiness.min_scale)
    assert math.isfinite(readiness.max_scale)
    assert readiness.max_scale >= readiness.min_scale > 0

    jac = finite_difference_jacobian(lambda _t, y: np.array([-2.0 * y[0], 3.0 * y[1]]), 0.0, np.array([1.0, 2.0]))
    diag = jacobian_diagnostic(jac)
    assert jac.shape == (2, 2)
    assert diag.finite is True
    assert diag.max_abs > 0

