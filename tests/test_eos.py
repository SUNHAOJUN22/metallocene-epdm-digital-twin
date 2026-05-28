import math

from epdm_sim.eos import cubic_eos_k_value, eos_k_values


def test_cubic_eos_k_value_finite_positive():
    value = cubic_eos_k_value("ethylene", 373.15, 1.0e6, eos="PR")
    assert math.isfinite(value)
    assert value > 0.0


def test_eos_k_values_returns_all_names():
    values = eos_k_values(["ethylene", "propylene", "ENB"], 373.15, 1.0e6, eos="SRK")
    assert set(values) == {"ethylene", "propylene", "ENB"}
    assert all(math.isfinite(v) and v > 0.0 for v in values.values())

