from epdm_sim.dynamic_core.adaptive_integrator import (
    adaptive_integrator_dataframe,
    adaptive_integrator_gate,
    adaptive_integrator_summary,
    integrate_with_adaptive_policy,
)
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode


def test_adaptive_integrator_default_dynamic_result():
    dynamic = simulate_template_semibatch_ode(solver_mode="explicit_bounded", total_time_min=4.0, dt_min=0.5)
    status = integrate_with_adaptive_policy(dynamic)
    df = adaptive_integrator_dataframe(dynamic)
    summary = adaptive_integrator_summary(dynamic)
    gate = adaptive_integrator_gate(dynamic)
    assert status["accepted_steps"] >= status["rejected_steps"]
    assert not df.empty
    assert summary["passed"]
    assert gate["passed"]

