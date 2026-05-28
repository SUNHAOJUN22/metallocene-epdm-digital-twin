from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.ode_events import end_reaction_event, feed_cutoff_event, quench_event, runaway_event


def test_ode_event_functions_cross_zero():
    assert quench_event(10.0, 10.0) == 0.0
    assert runaway_event(450.0, 450.0) == 0.0
    assert feed_cutoff_event(1.0e6, 1.0e6) == 0.0
    assert end_reaction_event(30.0, 30.0) == 0.0


def test_solve_ivp_mode_returns_profile_and_event_log():
    result = simulate_template_semibatch_ode(total_time_min=8.0, dt_min=2.0, solver_mode="solve_ivp_rk45")
    assert not result.profile.empty
    assert result.summary["solver_mode_requested"] == "solve_ivp_rk45"
    assert result.profile["polymer_mass_kg"].min() >= 0.0

