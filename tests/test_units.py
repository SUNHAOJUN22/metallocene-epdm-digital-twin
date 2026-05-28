import pytest

from epdm_sim.units import (
    assert_conversion_range,
    assert_heat_duty_sign,
    assert_mass_flow_nonnegative,
    assert_mole_fraction_sum,
    assert_pressure_Pa,
    assert_temperature_K,
    assert_weight_percent_sum,
    c_to_k,
    fraction_to_wt_percent,
    g_mol_to_kg_mol,
    kg_h_to_mol_h,
    kj_h_to_kw,
    k_to_c,
    kg_mol_to_g_mol,
    kw_to_kj_h,
    l_to_m3,
    m3_to_l,
    mol_L_to_mol_m3,
    mol_h_to_kg_h,
    mol_m3_to_mol_L,
    mpa_to_pa,
    pa_to_mpa,
    wt_percent_to_fraction,
)


def test_unit_conversions_are_reversible():
    assert mol_h_to_kg_h(kg_h_to_mol_h(28.054, 28.054), 28.054) == pytest.approx(28.054)
    assert mol_m3_to_mol_L(mol_L_to_mol_m3(1.2)) == pytest.approx(1.2)
    assert pa_to_mpa(mpa_to_pa(1.7)) == pytest.approx(1.7)
    assert k_to_c(c_to_k(100.0)) == pytest.approx(100.0)
    assert m3_to_l(l_to_m3(5.0)) == pytest.approx(5.0)
    assert kw_to_kj_h(kj_h_to_kw(7200.0)) == pytest.approx(7200.0)
    assert kg_mol_to_g_mol(g_mol_to_kg_mol(86.18)) == pytest.approx(86.18)
    assert fraction_to_wt_percent(wt_percent_to_fraction(12.5)) == pytest.approx(12.5)


def test_unit_assertions_accept_valid_values():
    assert_temperature_K(298.15)
    assert_pressure_Pa(101325.0)
    assert_mass_flow_nonnegative(0.0)
    assert_mole_fraction_sum({"a": 0.4, "b": 0.6})
    assert_weight_percent_sum({"C2": 54.3, "C3": 38.9, "ENB": 6.8})
    assert_heat_duty_sign(10.0, exothermic=True)
    assert_conversion_range(99.9, as_percent=True)


def test_unit_assertions_reject_invalid_values():
    with pytest.raises(ValueError):
        assert_temperature_K(0.0)
    with pytest.raises(ValueError):
        assert_pressure_Pa(-1.0)
    with pytest.raises(ValueError):
        assert_mass_flow_nonnegative(-0.01)
    with pytest.raises(ValueError):
        assert_mole_fraction_sum([0.2, 0.7])
    with pytest.raises(ValueError):
        assert_weight_percent_sum([50.0, 40.0])
    with pytest.raises(ValueError):
        assert_heat_duty_sign(-1.0, exothermic=True)
    with pytest.raises(ValueError):
        assert_conversion_range(1.1)
