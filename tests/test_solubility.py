import math

from epdm_sim.solubility import gas_liquid_saturation_table, liquid_saturation_concentration_mol_L


def test_gas_solubility_increases_with_pressure():
    low = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 0.3)
    high = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 1.0)
    assert high > low > 0.0


def test_solubility_temperature_response_finite():
    cold = liquid_saturation_concentration_mol_L("hydrogen", "hexane", 333.15, 0.5)
    hot = liquid_saturation_concentration_mol_L("hydrogen", "hexane", 393.15, 0.5)
    assert math.isfinite(cold)
    assert math.isfinite(hot)
    assert cold > 0.0 and hot > 0.0


def test_saturation_table_contains_core_gases():
    table = gas_liquid_saturation_table(373.15, 1.0, {"ethylene": 0.45, "propylene": 0.50, "hydrogen": 0.05})
    assert {"ethylene", "propylene", "hydrogen"}.issubset(set(table["component"]))
    assert (table["C_star_mol_L"] >= 0).all()

