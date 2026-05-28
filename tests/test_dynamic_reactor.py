import math

from epdm_sim.dynamic_reactor import DynamicReactorConfig, mixing_power, simulate_dynamic_reactor
from epdm_sim.flowsheet import load_default_config


def test_dynamic_reactor_profile_is_finite():
    cfg = load_default_config()
    dyn = DynamicReactorConfig(total_time_min=20.0, dt_min=2.0, rpm=500.0)
    result = simulate_dynamic_reactor(cfg, dyn)
    profile = result.time_profile()
    assert len(profile) > 5
    assert profile["T_C"].map(math.isfinite).all()
    assert profile["viscosity_Pa_s"].iloc[-1] > 0.0
    assert result.summary["recommended_rpm"] >= 100.0


def test_mixing_power_increases_with_rpm():
    cfg = load_default_config()
    low = mixing_power(cfg, DynamicReactorConfig(rpm=300.0), 0.003)
    high = mixing_power(cfg, DynamicReactorConfig(rpm=700.0), 0.003)
    assert high["mixing_power_kW"] > low["mixing_power_kW"]
    assert high["impeller_Re"] > low["impeller_Re"]
