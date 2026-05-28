from epdm_sim.dynamic_stability import check_dynamic_stability, dynamic_stability_dataframe
from epdm_sim.flowsheet import load_default_config
from epdm_sim.reactor import simulate_dynamic_semibatch_ode


def test_dynamic_ode_profile_stability_checks():
    cfg = load_default_config()
    result = simulate_dynamic_semibatch_ode(cfg, {"n_eval": 25, "total_time_min": 30})
    checks = check_dynamic_stability(result.profile)
    assert checks
    assert not [check for check in checks if not check.passed and check.severity == "error"]
    assert not dynamic_stability_dataframe(checks).empty


def test_quench_event_reduces_catalyst_activity():
    cfg = load_default_config()
    result = simulate_dynamic_semibatch_ode(cfg, {"n_eval": 30, "total_time_min": 30, "quench_active": True})
    assert result.profile["catalyst_active"].iloc[-1] < result.profile["catalyst_active"].iloc[5]
