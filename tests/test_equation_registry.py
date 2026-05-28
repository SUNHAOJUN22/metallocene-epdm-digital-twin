from epdm_sim.equation_registry import equation_registry_dataframe, load_equation_registry, validate_equation_registry


def test_equation_registry_loads_core_formulas_with_units():
    registry = load_equation_registry()
    assert "arrhenius_rate_constant" in registry
    assert "template_liquid_monomer_balance" in registry
    assert "template_energy_balance" in registry
    assert "darcy_weisbach_pressure_drop" in registry
    assert validate_equation_registry(registry) == []
    df = equation_registry_dataframe(registry)
    assert len(df) >= 18
    assert df["output_unit"].astype(str).str.len().gt(0).all()
