from pathlib import Path

from epdm_sim.utils import (
    c_to_k,
    clamp,
    data_path,
    engineering_error_percent,
    kg_h_to_mol_h,
    k_to_c,
    mol_h_to_kg_h,
    mpa_to_pa,
    normalize,
    pa_to_mpa,
    safe_divide,
    weighted_average,
)


def test_utils_unit_roundtrips_and_bounds():
    assert k_to_c(c_to_k(25.0)) == 25.0
    assert pa_to_mpa(mpa_to_pa(1.23)) == 1.23
    mol = kg_h_to_mol_h(1.5, 42.0)
    assert abs(mol_h_to_kg_h(mol, 42.0) - 1.5) < 1e-12
    assert clamp(5, 0, 3) == 3
    assert safe_divide(1, 0, 7) == 7
    assert sum(normalize({"a": 2.0, "b": 3.0}).values()) == 1.0
    assert weighted_average({"a": 10.0}, {"a": 2.0}) == 10.0
    assert engineering_error_percent(100, 105) == 5.0
    assert Path(data_path("components.json")).exists()
