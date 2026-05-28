from epdm_sim.numerics import (
    bounded,
    finite_dict,
    finite_or_default,
    nonnegative,
    normalize_to_sum,
    safe_exp,
    safe_log,
    safe_power,
    validate_kpi_finiteness,
)


def test_numerics_guards_are_finite_and_bounded():
    assert finite_or_default(float("nan"), 3.0) == 3.0
    assert nonnegative(-1.0) == 0.0
    assert bounded(12.0, 0.0, 10.0) == 10.0
    assert safe_exp(1000.0) < 1.0e36
    assert safe_log(0.0) < 0.0
    assert safe_power(-2.0, 0.5) == 0.0


def test_normalize_and_finite_dict():
    values = normalize_to_sum({"a": 2.0, "b": 2.0}, target=100.0)
    assert abs(sum(values.values()) - 100.0) < 1.0e-9
    assert finite_dict({"x": float("inf"), "y": 2.0}) == {"x": 0.0, "y": 2.0}


def test_validate_kpi_finiteness_detects_bad_values():
    assert validate_kpi_finiteness({"a": 1.0}) == []
    assert validate_kpi_finiteness({"a": float("nan")})
