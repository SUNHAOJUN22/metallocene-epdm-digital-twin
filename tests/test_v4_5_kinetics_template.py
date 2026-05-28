from epdm_sim.kinetics import (
    KineticParameters,
    calculate_template_conversions,
    calculate_template_polymer_segments,
    calculate_template_rates,
    reaction_rates,
)


def test_epdm_template_rates_keep_legacy_direction():
    concentrations = {"ethylene": 1.0, "propylene": 1.0, "ENB": 0.2}
    legacy = reaction_rates(concentrations, 1.0e-6, 373.15, 1.0, KineticParameters())
    templated = calculate_template_rates(
        "EPDM_EPM_metallocene_solution",
        concentrations,
        {"Cstar_mol_L": 1.0e-6},
        {"temperature_K": 373.15, "pressure_MPa": 1.0},
        KineticParameters(),
    )
    assert templated.r_E_mol_L_h > 0
    assert templated.r_P_mol_L_h > 0
    assert templated.r_ENB_mol_L_h > 0
    assert templated.r_E_mol_L_h == legacy.r_E_mol_L_h
    assert set(templated.rates_mol_L_h) == {"ethylene", "propylene", "ENB"}


def test_generic_terpolymerization_template_runs_with_warnings():
    result = calculate_template_rates(
        "generic_terpolymerization_apparent",
        {"monomer_A": 1.0, "monomer_B": 0.5, "monomer_C": 0.2},
        1.0e-6,
        {"temperature_K": 360.0, "pressure_MPa": 1.0},
    )
    assert all(value >= 0 for value in result.rates_mol_L_h.values())
    assert result.warnings


def test_unknown_template_falls_back_without_crash():
    result = calculate_template_rates("missing_template", {"ethylene": 1.0}, 1.0e-6, {"temperature_K": 373.15})
    assert result.r_E_mol_L_h >= 0
    assert any("Unknown reaction template" in warning for warning in result.warnings)


def test_template_conversions_bounded_and_segments_mass_consistent():
    feed = {"ethylene": 10.0, "propylene": 5.0, "ENB": 1.0}
    consumed = {"ethylene": 20.0, "propylene": 1.0, "ENB": 0.5}
    conversions = calculate_template_conversions("EPDM_EPM_metallocene_solution", feed, consumed)
    assert all(0.0 <= value <= 1.0 for value in conversions.values())
    segments = calculate_template_polymer_segments("EPDM_EPM_metallocene_solution", consumed)
    expected = 20.0 * 28.054 / 1000.0 + 1.0 * 42.081 / 1000.0 + 0.5 * 120.19 / 1000.0
    assert abs(sum(segments.values()) - expected) < 1.0e-12
